"""Small data holders passed between the ML code and the rest of the app."""
from dataclasses import dataclass

from app.enums import ProblemType, Severity


@dataclass
class RawDetection:
    problem_type: ProblemType
    confidence: float
    bbox_x_min: float   # all four box values are fractions (0 to 1) of the photo size
    bbox_y_min: float
    bbox_x_max: float
    bbox_y_max: float


@dataclass
class ScoredDetection(RawDetection):
    severity_suggested: Severity = Severity.LOW


@dataclass
class InferenceResult:
    model_available: bool
    model_version: str | None
    image_width: int | None
    image_height: int | None
    detections: list[ScoredDetection]
    message: str | None = None   # reason, when the model is not available
