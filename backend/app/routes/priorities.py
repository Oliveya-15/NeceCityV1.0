from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import problem_service

router = APIRouter(prefix="/priorities", tags=["priorities"])


@router.get("")
def get_priorities(city_id: int, limit: int = 20, unresolved_only: bool = True, db: Session = Depends(get_db)):
    """Problems of a city ordered by risk score (highest first)."""
    problems = problem_service.list_priorities(db, city_id, limit, unresolved_only)
    return [
        {
            "id": p.id,
            "problem_type": p.problem_type.value,
            "severity": p.severity.value,
            "status": p.status.value,
            "latitude": p.location.latitude,
            "longitude": p.location.longitude,
            "road_name": p.location.road_name,
            "risk_score": p.risk_score.score if p.risk_score else 0,
            "recommended_action": p.risk_score.recommended_action if p.risk_score else None,
            "recurrence_count": p.recurrence_count,
        }
        for p in problems
    ]
