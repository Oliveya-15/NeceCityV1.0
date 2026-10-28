"""The detector used by the app. It loads the ONNX model once and runs it on photos.

If the model file is missing the app still starts: the detector reports
"not available" and the user can add problems manually.
"""
from app.config import get_settings
from app.ml.classes import CLASS_INDEX
from app.ml.postprocessing import add_severity
from app.ml.schema import InferenceResult, RawDetection
from app.log import get_logger

logger = get_logger(__name__)


class Detector:
    def __init__(self):
        self.settings = get_settings()
        self.model = None
        self.unavailable_reason: str | None = None
        self._load()

    def _load(self) -> None:
        path = self.settings.model_file
        if not path.exists():
            self.unavailable_reason = (
                f"Model file not found at {path}. Put nececity_yolo.onnx in the ml/weights folder."
            )
            logger.warning(self.unavailable_reason)
            return
        try:
            from app.ml.onnx_runtime import OnnxYolo
            self.model = OnnxYolo(str(path))
            logger.info("Model loaded: %s", path.name)
        except Exception as exc:  # the app must still start if the model cannot be loaded
            self.unavailable_reason = f"The model could not be loaded: {exc}"
            logger.error(self.unavailable_reason)

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    @property
    def model_version(self) -> str:
        return self.settings.MODEL_VERSION

    def predict(self, image_path: str, width: int, height: int) -> InferenceResult:
        if not self.is_ready:
            return InferenceResult(
                model_available=False, model_version=None, image_width=width, image_height=height,
                detections=[], message=self.unavailable_reason,
            )

        s = self.settings
        boxes = self.model.predict(
            image_path,
            conf=s.MODEL_MIN_CONFIDENCE,
            iou=s.MODEL_IOU_THRESHOLD,
            imgsz=s.MODEL_IMAGE_SIZE,
            max_det=s.MODEL_MAX_DETECTIONS,
        )
        raw = []
        for box in boxes:
            problem_type = CLASS_INDEX.get(box.class_id)
            if problem_type is None:
                continue  # the model gave a class number we do not know
            raw.append(RawDetection(
                problem_type=problem_type,
                confidence=round(box.confidence, 4),
                bbox_x_min=round(box.x_min, 4), bbox_y_min=round(box.y_min, 4),
                bbox_x_max=round(box.x_max, 4), bbox_y_max=round(box.y_max, 4),
            ))
        return InferenceResult(
            model_available=True, model_version=self.model_version,
            image_width=width, image_height=height, detections=add_severity(raw),
        )


_detector: Detector | None = None


def get_detector() -> Detector:
    """One shared detector for the whole app (the model is loaded only once)."""
    global _detector
    if _detector is None:
        _detector = Detector()
    return _detector
