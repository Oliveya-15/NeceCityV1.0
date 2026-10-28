"""City list and the numbers shown on the Dashboard."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import ProblemStatus, ProblemType, Severity
from app.models import City, Problem

# how much each unresolved problem pulls the health score down
SEVERITY_PENALTY = {Severity.LOW: 5, Severity.MEDIUM: 15, Severity.HIGH: 30, Severity.CRITICAL: 50}


def list_cities(db: Session) -> list[City]:
    return list(db.execute(select(City).where(City.is_active.is_(True)).order_by(City.name)).scalars())


def get_city(db: Session, city_id: int) -> City | None:
    return db.get(City, city_id)


def health_label(score: float) -> str:
    if score >= 80:
        return "Good"
    if score >= 60:
        return "Fair"
    if score >= 40:
        return "Poor"
    return "Critical"


def count_by(db: Session, column, city_id: int) -> dict:
    """{value: number of problems} for one column, e.g. severity, for one city."""
    rows = db.execute(
        select(column, func.count(Problem.id)).where(Problem.city_id == city_id).group_by(column)
    ).all()
    return dict(rows)


def get_city_summary(db: Session, city: City) -> dict:
    severity_counts = count_by(db, Problem.severity, city.id)
    status_counts = count_by(db, Problem.status, city.id)
    type_counts = count_by(db, Problem.problem_type, city.id)

    severity_breakdown = {s.value: severity_counts.get(s, 0) for s in Severity}
    status_breakdown = {s.value: status_counts.get(s, 0) for s in ProblemStatus}
    type_breakdown = {t.value: type_counts.get(t, 0) for t in ProblemType}

    total = sum(status_breakdown.values())
    resolved = status_breakdown[ProblemStatus.RESOLVED.value]

    # health score: starts at 100 and goes down with the number and severity of open problems
    open_severities = db.execute(
        select(Problem.severity).where(Problem.city_id == city.id, Problem.status != ProblemStatus.RESOLVED)
    ).scalars().all()
    if open_severities:
        average_penalty = sum(SEVERITY_PENALTY[s] for s in open_severities) / len(open_severities)
        volume = min(len(open_severities) / 25, 1.0)
        health = max(0.0, 100 - average_penalty * (0.4 + 0.6 * volume))
    else:
        health = 100.0

    has_demo = db.execute(
        select(func.count(Problem.id)).where(Problem.city_id == city.id, Problem.is_demo.is_(True))
    ).scalar_one() > 0

    return {
        "city": city,
        "total_problems": total,
        "critical_problems": severity_breakdown["critical"],
        "high_priority_problems": severity_breakdown["high"],
        "resolved_problems": resolved,
        "unresolved_problems": total - resolved,
        "severity_breakdown": severity_breakdown,
        "status_breakdown": status_breakdown,
        "problem_type_breakdown": type_breakdown,
        "infrastructure_health_score": round(health, 1),
        "infrastructure_health_label": health_label(health),
        "has_demo_data": has_demo,
    }
