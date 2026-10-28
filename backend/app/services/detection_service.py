"""Saving photos, running the model, and turning reviewed detections into problems."""
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.enums import DetectionStatus, ImageSource, ProblemStatus, ProblemType, RoadImportance, Severity
from app.ml.detector import get_detector
from app.ml.preprocessing import ValidatedImage
from app.models import City, Detection, Image, Location, Problem
from app.schemas import DetectionVerifyRequest
from app.services.problem_service import find_nearby_problems, recompute_and_store_risk

USER_MARKED = "user-marked"        # model_version of boxes drawn by the user
DUPLICATE_RADIUS_M = 30            # same type of problem within 30 m = same problem
EXTENSION = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


def save_uploaded_image(db: Session, raw_bytes: bytes, checked: ValidatedImage, original_name: str | None) -> Image:
    # a random file name, so two uploads can never overwrite each other
    file_path = get_settings().upload_folder / f"{uuid.uuid4().hex}{EXTENSION.get(checked.content_type, '.jpg')}"
    file_path.write_bytes(raw_bytes)

    image = Image(
        file_path=str(file_path),
        original_filename=(original_name or "")[:255] or None,
        content_type=checked.content_type,
        file_size_bytes=len(raw_bytes),
        width=checked.width,
        height=checked.height,
        source=ImageSource.UPLOAD,
    )
    db.add(image)
    db.flush()  # gives the image its id without finishing the transaction
    return image


def run_inference_and_store(db: Session, image: Image):
    """Run the model on a saved image and store every box as a 'pending review' detection."""
    result = get_detector().predict(image.file_path, image.width, image.height)
    rows = []
    for det in result.detections:
        row = Detection(
            image_id=image.id,
            problem_type=det.problem_type,
            confidence=det.confidence,
            bbox_x_min=det.bbox_x_min, bbox_y_min=det.bbox_y_min,
            bbox_x_max=det.bbox_x_max, bbox_y_max=det.bbox_y_max,
            model_version=result.model_version or "unknown",
            severity_suggested=det.severity_suggested,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return result, rows


def create_user_marked_detection(
    db: Session, image: Image, problem_type: ProblemType, severity: Severity,
    x_min: float, y_min: float, x_max: float, y_max: float,
) -> Detection:
    """A box drawn by the user for a problem the model missed (confidence is 1.0)."""
    row = Detection(
        image_id=image.id, problem_type=problem_type, confidence=1.0,
        bbox_x_min=round(x_min, 4), bbox_y_min=round(y_min, 4),
        bbox_x_max=round(x_max, 4), bbox_y_max=round(y_max, 4),
        model_version=USER_MARKED, severity_suggested=severity,
    )
    db.add(row)
    db.flush()
    return row


def make_description(city_name: str, problem_type: ProblemType, severity: Severity, road_name: str | None) -> str:
    where = f"on {road_name}" if road_name else "at the reported location"
    label = problem_type.value.replace("_", " ")
    return f"A {severity.value} severity {label} was reported {where} in {city_name}."


def place_or_update_problem(
    db: Session, city_id: int, problem_type: ProblemType, severity: Severity,
    latitude: float, longitude: float, road_name: str | None = None,
    road_importance: str = "local", source_detection_id: int | None = None,
) -> Problem:
    """Save a confirmed problem.

    If an unresolved problem of the same type is already within 30 m, we do not create
    a duplicate: its recurrence count goes up instead (and its severity if the new one is higher)."""
    nearby = find_nearby_problems(db, city_id, latitude, longitude, DUPLICATE_RADIUS_M, problem_type=problem_type)
    if nearby:
        existing = nearby[0][0]
        existing.recurrence_count += 1
        existing.last_detected_at = datetime.utcnow()
        if SEVERITY_ORDER.index(severity) > SEVERITY_ORDER.index(existing.severity):
            existing.severity = severity
        recompute_and_store_risk(db, existing)
        return existing

    location = Location(
        city_id=city_id, latitude=latitude, longitude=longitude,
        road_name=road_name, road_importance=RoadImportance(road_importance),
    )
    db.add(location)
    db.flush()

    city = db.get(City, city_id)
    problem = Problem(
        city_id=city_id,
        location_id=location.id,
        source_detection_id=source_detection_id,
        problem_type=problem_type,
        severity=severity,
        status=ProblemStatus.VERIFIED,  # a person has checked it, so it starts as Verified
        description=make_description(city.name if city else "the city", problem_type, severity, road_name),
        recurrence_count=1,
        is_demo=False,
    )
    db.add(problem)
    db.flush()
    recompute_and_store_risk(db, problem)
    return problem


def verify_detection(db: Session, detection: Detection, payload: DetectionVerifyRequest) -> Problem | None:
    """Apply the reviewer's decision. Returns the problem when confirmed, None when rejected."""
    if payload.action == "reject":
        detection.status = DetectionStatus.REJECTED
        detection.reviewed_at = datetime.utcnow()
        return None
    if payload.action != "confirm":
        raise ValueError("action must be 'confirm' or 'reject'")

    severity = Severity(payload.final_severity) if payload.final_severity else detection.severity_suggested
    detection.status = DetectionStatus.CONFIRMED
    detection.reviewed_severity = severity
    detection.reviewed_at = datetime.utcnow()

    return place_or_update_problem(
        db, payload.city_id, detection.problem_type, severity, payload.latitude, payload.longitude,
        road_name=payload.road_name, road_importance=payload.road_importance,
        source_detection_id=detection.id,
    )
