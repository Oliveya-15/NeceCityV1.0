"""Reading and updating problems (lists, map data, status changes, risk score)."""
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.enums import STATUS_ORDER, ProblemStatus, ProblemType, Severity
from app.geo import bounding_box, haversine_m
from app.models import Detection, Location, Problem, RiskScore
from app.risk import DENSITY_RADIUS_M, compute_risk


class InvalidStatusChange(ValueError):
    pass


def _with_location_and_risk():
    # load the location and risk score together with each problem (avoids many small queries)
    return select(Problem).options(joinedload(Problem.location), joinedload(Problem.risk_score))


def list_problems(
    db: Session, city_id: int | None, problem_type: ProblemType | None, severity: Severity | None,
    status: ProblemStatus | None, page: int, page_size: int,
):
    query = _with_location_and_risk()
    if city_id is not None:
        query = query.where(Problem.city_id == city_id)
    if problem_type is not None:
        query = query.where(Problem.problem_type == problem_type)
    if severity is not None:
        query = query.where(Problem.severity == severity)
    if status is not None:
        query = query.where(Problem.status == status)

    total = db.execute(select(func.count()).select_from(query.order_by(None).subquery())).scalar_one()
    query = query.order_by(Problem.first_detected_at.desc()).offset((page - 1) * page_size).limit(page_size)
    return list(db.execute(query).unique().scalars()), total


def list_map_problems(
    db: Session, city_id: int, problem_types: list | None, severities: list | None, statuses: list | None
) -> list[Problem]:
    query = _with_location_and_risk().where(Problem.city_id == city_id)
    if problem_types:
        query = query.where(Problem.problem_type.in_(problem_types))
    if severities:
        query = query.where(Problem.severity.in_(severities))
    if statuses:
        query = query.where(Problem.status.in_(statuses))
    return list(db.execute(query).unique().scalars())


def get_problem_detail(db: Session, problem_id: int) -> Problem | None:
    query = (
        select(Problem)
        .where(Problem.id == problem_id)
        .options(
            joinedload(Problem.location),
            joinedload(Problem.risk_score),
            joinedload(Problem.source_detection).joinedload(Detection.image),
        )
    )
    return db.execute(query).unique().scalar_one_or_none()


def find_nearby_problems(
    db: Session, city_id: int, latitude: float, longitude: float, radius_m: float,
    problem_type: ProblemType | None = None, exclude_id: int | None = None,
) -> list[tuple[Problem, float]]:
    """Unresolved problems within radius_m metres of a point, closest first.
    Returns (problem, distance in metres) pairs.

    Step 1: the database keeps only the problems inside a small square around the point.
    Step 2: we measure the exact distance of each one with the haversine formula."""
    min_lat, max_lat, min_lon, max_lon = bounding_box(latitude, longitude, radius_m)
    query = (
        _with_location_and_risk()
        .join(Location, Problem.location_id == Location.id)
        .where(
            Problem.city_id == city_id,
            Problem.status != ProblemStatus.RESOLVED,
            Location.latitude.between(min_lat, max_lat),
            Location.longitude.between(min_lon, max_lon),
        )
    )
    if problem_type is not None:
        query = query.where(Problem.problem_type == problem_type)
    if exclude_id is not None:
        query = query.where(Problem.id != exclude_id)

    found = []
    for problem in db.execute(query).unique().scalars():
        distance = haversine_m(latitude, longitude, problem.location.latitude, problem.location.longitude)
        if distance <= radius_m:
            found.append((problem, distance))
    found.sort(key=lambda pair: pair[1])
    return found


def recompute_and_store_risk(db: Session, problem: Problem) -> RiskScore:
    """Work out the risk score of a problem and save it (creates or updates the row)."""
    nearby = find_nearby_problems(
        db, problem.city_id, problem.location.latitude, problem.location.longitude,
        DENSITY_RADIUS_M, exclude_id=problem.id,
    )
    result = compute_risk(problem.severity, problem.recurrence_count, len(nearby), problem.location.road_importance)

    if problem.risk_score is None:
        problem.risk_score = RiskScore(problem_id=problem.id, score=0, components={}, weights_version="", recommended_action="")
        db.add(problem.risk_score)
    problem.risk_score.score = result.score
    problem.risk_score.components = result.components
    problem.risk_score.reasons = result.reasons
    problem.risk_score.weights_version = result.weights_version
    problem.risk_score.recommended_action = result.recommended_action
    return problem.risk_score


def update_problem_status(problem: Problem, new_status: ProblemStatus) -> None:
    """Move a problem one step along Detected -> Verified -> In Progress -> Resolved."""
    step = abs(STATUS_ORDER.index(new_status) - STATUS_ORDER.index(problem.status))
    if step > 1:
        raise InvalidStatusChange(
            f"Cannot move status from '{problem.status.value}' directly to '{new_status.value}'. "
            "Problems must progress through the lifecycle one step at a time."
        )
    problem.status = new_status


def list_priorities(db: Session, city_id: int, limit: int, unresolved_only: bool) -> list[Problem]:
    """Problems with the highest risk score first."""
    query = (
        _with_location_and_risk()
        .join(RiskScore, Problem.id == RiskScore.problem_id)
        .where(Problem.city_id == city_id)
    )
    if unresolved_only:
        query = query.where(Problem.status != ProblemStatus.RESOLVED)
    query = query.order_by(desc(RiskScore.score)).limit(limit)
    return list(db.execute(query).unique().scalars())
