"""All settings of the backend. Values come from environment variables
(or from the .env file when running locally)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# the "backend" folder; relative paths in the settings are resolved from here
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/nececity"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # image upload rules
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 8
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # object detection model (ONNX file exported from the trained YOLOv8n)
    MODEL_PATH: str = "../ml/weights/nececity_yolo.onnx"
    MODEL_VERSION: str = "nececity-yolov8n"
    MODEL_IMAGE_SIZE: int = 640
    # a box at or above this confidence is treated as "confident"
    MODEL_CONFIDENCE_THRESHOLD: float = 0.35
    # boxes between MIN and THRESHOLD are still shown, marked "low confidence"
    MODEL_MIN_CONFIDENCE: float = 0.10
    MODEL_IOU_THRESHOLD: float = 0.45
    MODEL_MAX_DETECTIONS: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def model_file(self) -> Path:
        path = Path(self.MODEL_PATH)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

    @property
    def upload_folder(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
