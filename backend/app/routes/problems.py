from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import ProblemStatus, ProblemType, Severity
from app.models import Image
from app.schemas import (
    ManualProblemRequest,
    ManualProblemResponse,
    PaginatedProblems,
    ProblemDetailOut,
    ProblemStatusUpdate,
)
from app.services import problem_service
from app.services.detection_service import USER_MARKED, place_or_update_problem

router = APIRouter(prefix="/problems", tags=["problems"])


def image_url(image: Image) -> dict:
    return {"id": image.id, "url": f"/uploads/{image.file_path.split('/')[-1]}", "source": image.source.value}


def to_list_item(p) -> dict:
    return {
        "id": p.id,
        "problem_type": p.problem_type.value,
        "severity": p.severity.value,
        "status": p.status.value,
        "latitude": p.location.latitude,
        "longitude": p.location.longitude,
        "road_name": p.location.road_name,
        "recurrence_count": p.recurrence_count,
        "is_demo": p.is_demo,
        "risk_score": p.risk_score.score if p.risk_score else None,
        "first_detected_at": p.first_detected_at,
        "last_detected_at": p.last_detected_at,
    }


@router.get("", response_model=PaginatedProblems)
def list_problems(
    city_id: int | None = None,
    problem_type: ProblemType | None = None,
    severity: Severity | None = None,
    status: ProblemStatus | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
):
    items, total = problem_service.list_problems(db, city_id, problem_type, severity, status, page, page_size)
    return {"items": [to_list_item(p) for p in items], "total": total, "page": page, "page_size": page_size}


@router.post("/manual", response_model=ManualProblemResponse)
def create_manual_problem(payload: ManualProblemRequest, db: Session = Depends(get_db)):
    """Add a problem without the model (when the model is off or missed it)."""
    try:
        problem_type = ProblemType(payload.problem_type)
        severity = Severity(payload.severity)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    problem = place_or_update_problem(
        db, payload.city_id, problem_type, severity, payload.latitude, payload.longitude,
        road_name=payload.road_name, road_importance=payload.road_importance,
    )
    if payload.image_id is not None:
        image = db.get(Image, payload.image_id)
        if image is not None:
            image.location_id = problem.location_id
    db.commit()
    return ManualProblemResponse(problem_id=problem.id)


@router.get("/{problem_id}", response_model=ProblemDetailOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = problem_service.get_problem_detail(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"Problem {problem_id} not found.")

    # the photo: the one the problem came from, otherwise any photo linked to the same location
    image = None
    if problem.source_detection is not None:
        image = problem.source_detection.image
    if image is None:
        image = db.execute(
            select(Image).where(Image.location_id == problem.location_id).order_by(Image.uploaded_at.desc())
        ).scalars().first()

    detection = problem.source_detection
    return {
        "id": problem.id,
        "problem_type": problem.problem_type.value,
        "severity": problem.severity.value,
        "status": problem.status.value,
        "description": problem.description,
        "recurrence_count": problem.recurrence_count,
        "is_demo": problem.is_demo,
        "location": problem.location,
        "risk": problem.risk_score,
        "image": image_url(image) if image else None,
        "confidence": detection.confidence if detection and detection.model_version != USER_MARKED else None,
        "first_detected_at": problem.first_detected_at,
        "last_detected_at": problem.last_detected_at,
    }


@router.patch("/{problem_id}/status", response_model=ProblemDetailOut)
def update_status(problem_id: int, payload: ProblemStatusUpdate, db: Session = Depends(get_db)):
    problem = problem_service.get_problem_detail(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"Problem {problem_id} not found.")
    try:
        new_status = ProblemStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status '{payload.status}'.")
    try:
        problem_service.update_problem_status(problem, new_status)
    except problem_service.InvalidStatusChange as error:
        raise HTTPException(status_code=409, detail=str(error))
    db.commit()
    return get_problem(problem_id, db)
