"""Tests of the machine-learning helpers (none of them needs the model file)."""
import io

import pytest
from PIL import Image

from app.enums import ProblemType, Severity
from app.ml.detector import Detector
from app.ml.postprocessing import add_severity, relative_area, suggest_severity
from app.ml.preprocessing import ImageValidationError, validate_image_upload
from app.ml.schema import RawDetection


def box(problem_type, x1, y1, x2, y2):
    return RawDetection(ProblemType(problem_type), 0.8, x1, y1, x2, y2)


def picture(width, height, fmt="JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (100, 100, 100)).save(buffer, fmt)
    return buffer.getvalue()


# ---------- severity suggestion ----------
@pytest.mark.parametrize("problem_type, area_box, expected", [
    ("open_drain", (0.1, 0.1, 0.7, 0.7), Severity.CRITICAL),
    ("pothole", (0.4, 0.4, 0.5, 0.5), Severity.MEDIUM),
    ("garbage", (0.4, 0.4, 0.45, 0.45), Severity.LOW),
    ("damaged_road_sign", (0.0, 0.0, 1.0, 1.0), Severity.HIGH),
    ("road_damage", (0.2, 0.2, 0.6, 0.6), Severity.CRITICAL),
])
def test_severity_suggestion(problem_type, area_box, expected):
    assert suggest_severity(box(problem_type, *area_box)) == expected


def test_bigger_box_never_gives_a_lower_severity():
    order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    small = suggest_severity(box("pothole", 0.4, 0.4, 0.45, 0.45))
    large = suggest_severity(box("pothole", 0.1, 0.1, 0.9, 0.9))
    assert order.index(large) >= order.index(small)


def test_relative_area_is_capped_at_one():
    assert relative_area(box("pothole", 0, 0, 1, 1)) == 1.0


def test_add_severity_keeps_the_box_values():
    result = add_severity([box("pothole", 0.1, 0.2, 0.3, 0.4)])[0]
    assert (result.bbox_x_min, result.bbox_y_max) == (0.1, 0.4)
    assert result.severity_suggested in Severity


# ---------- image validation ----------
def test_valid_jpeg_is_accepted():
    checked = validate_image_upload(picture(800, 600), "image/jpeg")
    assert (checked.width, checked.height) == (800, 600)


@pytest.mark.parametrize("data, content_type, message", [
    pytest.param(picture(800, 600), "application/pdf", "Unsupported file type", id="wrong-type"),
    pytest.param(b"\x00" * (9 * 1024 * 1024), "image/jpeg", "8MB", id="too-big"),
    pytest.param(b"this is not an image", "image/jpeg", "not a valid", id="corrupt"),
    pytest.param(picture(20, 20), "image/jpeg", "too small", id="tiny"),
])
def test_bad_uploads_are_rejected(data, content_type, message):
    with pytest.raises(ImageValidationError, match=message):
        validate_image_upload(data, content_type)


# ---------- detector without a model ----------
def test_detector_without_model_file_reports_not_available(monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "missing.onnx"))
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        detector = Detector()
        assert not detector.is_ready
        result = detector.predict("whatever.jpg", 100, 100)
        assert result.model_available is False
        assert result.detections == []
        assert "not found" in result.message
    finally:
        get_settings.cache_clear()
