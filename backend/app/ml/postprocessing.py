"""Suggests a severity for every detected box.

This is a simple rule, NOT another AI model:
    severity score = 0.6 x (how serious this type of problem usually is)
                   + 0.4 x (how big the box is on the photo)
The person reviewing the detection can always change the suggested severity.
"""
from app.enums import ProblemType, Severity
from app.ml.schema import RawDetection, ScoredDetection

# how serious each problem type usually is (0 to 1)
TYPE_WEIGHT = {
    ProblemType.POTHOLE: 0.65,
    ProblemType.ROAD_DAMAGE: 0.70,
    ProblemType.OPEN_DRAIN: 0.75,
    ProblemType.WATERLOGGING: 0.60,
    ProblemType.GARBAGE: 0.35,
    ProblemType.DAMAGED_ROAD_SIGN: 0.30,
}

# (minimum score, severity), checked from the top
SEVERITY_BANDS = [
    (0.75, Severity.CRITICAL),
    (0.55, Severity.HIGH),
    (0.35, Severity.MEDIUM),
    (0.0, Severity.LOW),
]


def relative_area(det: RawDetection) -> float:
    width = max(det.bbox_x_max - det.bbox_x_min, 0.0)
    height = max(det.bbox_y_max - det.bbox_y_min, 0.0)
    # a box covering about 1/6 of the photo already counts as "large"
    return min(width * height * 6, 1.0)


def suggest_severity(det: RawDetection) -> Severity:
    score = 0.6 * TYPE_WEIGHT.get(det.problem_type, 0.5) + 0.4 * relative_area(det)
    for minimum, severity in SEVERITY_BANDS:
        if score >= minimum:
            return severity
    return Severity.LOW


def add_severity(raw_detections: list[RawDetection]) -> list[ScoredDetection]:
    return [
        ScoredDetection(
            problem_type=d.problem_type,
            confidence=d.confidence,
            bbox_x_min=d.bbox_x_min,
            bbox_y_min=d.bbox_y_min,
            bbox_x_max=d.bbox_x_max,
            bbox_y_max=d.bbox_y_max,
            severity_suggested=suggest_severity(d),
        )
        for d in raw_detections
    ]
