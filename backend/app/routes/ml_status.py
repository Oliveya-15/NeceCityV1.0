from fastapi import APIRouter

from app.ml.detector import get_detector

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/status")
def ml_status():
    """Is the detection model loaded? (shown as a badge in the top bar)"""
    detector = get_detector()
    return {
        "model_available": detector.is_ready,
        "model_version": detector.model_version if detector.is_ready else None,
        "unavailable_reason": detector.unavailable_reason,
        "training_data_warning": None,
    }
