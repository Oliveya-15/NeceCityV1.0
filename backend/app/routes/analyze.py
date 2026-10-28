from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.log import get_logger
from app.ml.preprocessing import ImageValidationError, validate_image_upload
from app.schemas import AnalyzeImageResponse, BoundingBox, DetectionOut
from app.services.detection_service import run_inference_and_store, save_uploaded_image

router = APIRouter(prefix="/analyze", tags=["analyze"])
logger = get_logger(__name__)


@router.post("/image", response_model=AnalyzeImageResponse)
def analyze_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a photo: check it, save it, run the model, return the boxes for review."""
    raw_bytes = file.file.read()
    try:
        checked = validate_image_upload(raw_bytes, file.content_type or "")
    except ImageValidationError as error:
        raise HTTPException(status_code=422, detail=str(error))

    image = save_uploaded_image(db, raw_bytes, checked, file.filename)
    try:
        result, rows = run_inference_and_store(db, image)
    except Exception as error:  # a model failure must not crash the API
        logger.error("Inference failed for image %s: %s", image.id, error)
        db.commit()  # keep the uploaded photo
        raise HTTPException(status_code=500, detail="Inference failed. The image was saved; please try again.")
    db.commit()

    confident_from = get_settings().MODEL_CONFIDENCE_THRESHOLD
    return AnalyzeImageResponse(
        image_id=image.id,
        model_available=result.model_available,
        model_version=result.model_version,
        message=result.message,
        image_width=result.image_width,
        image_height=result.image_height,
        detections=[
            DetectionOut(
                id=row.id,
                problem_type=row.problem_type.value,
                confidence=row.confidence,
                low_confidence=row.confidence < confident_from,
                severity_suggested=row.severity_suggested.value,
                bbox=BoundingBox(x_min=row.bbox_x_min, y_min=row.bbox_y_min, x_max=row.bbox_x_max, y_max=row.bbox_y_max),
            )
            for row in rows
        ],
    )
