from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import ProblemStatus, ProblemType, Severity
from app.services import problem_service

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/problems")
def map_problems(
    city_id: int,
    problem_type: list[ProblemType] | None = Query(default=None),
    severity: list[Severity] | None = Query(default=None),
    status: list[ProblemStatus] | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Every problem of a city for the map, optionally filtered by type, severity and status."""
    problems = problem_service.list_map_problems(db, city_id, problem_type, severity, status)
    return [
        {
            "id": p.id,
            "problem_type": p.problem_type.value,
            "severity": p.severity.value,
            "status": p.status.value,
            "latitude": p.location.latitude,
            "longitude": p.location.longitude,
            "road_name": p.location.road_name,
            "risk_score": p.risk_score.score if p.risk_score else None,
            "recurrence_count": p.recurrence_count,
            "last_detected_at": p.last_detected_at,
        }
        for p in problems
    ]
