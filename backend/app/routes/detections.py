from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import ProblemType, Severity
from app.models import Detection, Image
from app.schemas import (
    BoundingBox,
    DetectionOut,
    DetectionVerifyRequest,
    DetectionVerifyResponse,
    UserRegionRequest,
)
from app.services.detection_service import create_user_marked_detection, verify_detection

router = APIRouter(prefix="/detections", tags=["detections"])


@router.post("/user-region", response_model=DetectionOut)
def add_user_region(payload: UserRegionRequest, db: Session = Depends(get_db)):
    """The user drew a box around a problem the model did not find."""
    image = db.get(Image, payload.image_id)
    if image is None:
        raise HTTPException(status_code=404, detail=f"Image {payload.image_id} not found.")
    try:
        problem_type = ProblemType(payload.problem_type)
        severity = Severity(payload.severity)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    row = create_user_marked_detection(
        db, image, problem_type, severity, payload.x_min, payload.y_min, payload.x_max, payload.y_max
    )
    db.commit()
    return DetectionOut(
        id=row.id,
        problem_type=row.problem_type.value,
        confidence=row.confidence,
        severity_suggested=row.severity_suggested.value,
        bbox=BoundingBox(x_min=row.bbox_x_min, y_min=row.bbox_y_min, x_max=row.bbox_x_max, y_max=row.bbox_y_max),
        source="user",
        low_confidence=False,
    )


@router.post("/{detection_id}/verify", response_model=DetectionVerifyResponse)
def verify(detection_id: int, payload: DetectionVerifyRequest, db: Session = Depends(get_db)):
    """The reviewer confirms or rejects a detection."""
    detection = db.get(Detection, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail=f"Detection {detection_id} not found.")
    if detection.status.value != "pending_review":
        raise HTTPException(status_code=409, detail=f"Detection {detection_id} has already been reviewed.")
    try:
        problem = verify_detection(db, detection, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    db.commit()
    return DetectionVerifyResponse(
        detection_id=detection.id, status=detection.status.value, problem_id=problem.id if problem else None
    )
