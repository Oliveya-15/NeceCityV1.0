"""Checks an uploaded file before it is saved or given to the model."""
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.config import get_settings

MIN_SIDE_PX = 64
MAX_SIDE_PX = 8000


class ImageValidationError(ValueError):
    """Raised when the uploaded file is not acceptable. The message is shown to the user."""


@dataclass
class ValidatedImage:
    width: int
    height: int
    content_type: str


def validate_image_upload(raw_bytes: bytes, content_type: str) -> ValidatedImage:
    settings = get_settings()

    if content_type not in settings.ALLOWED_IMAGE_TYPES:
        allowed = ", ".join(settings.ALLOWED_IMAGE_TYPES)
        raise ImageValidationError(f"Unsupported file type '{content_type}'. Allowed types: {allowed}.")

    if len(raw_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ImageValidationError(f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.")

    try:
        with Image.open(BytesIO(raw_bytes)) as img:
            img.verify()  # quick check that the file is a real, undamaged image
        with Image.open(BytesIO(raw_bytes)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError("The uploaded file is not a valid or is a corrupted image.") from exc

    if width < MIN_SIDE_PX or height < MIN_SIDE_PX:
        raise ImageValidationError(f"Image is too small (minimum {MIN_SIDE_PX}x{MIN_SIDE_PX}px).")
    if width > MAX_SIDE_PX or height > MAX_SIDE_PX:
        raise ImageValidationError(f"Image is too large (maximum {MAX_SIDE_PX}x{MAX_SIDE_PX}px).")

    return ValidatedImage(width=width, height=height, content_type=content_type)
