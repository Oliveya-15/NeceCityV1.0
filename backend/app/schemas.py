"""Shapes of the data that the API sends and receives (Pydantic models)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------- cities ----------
class CityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    state: str
    center_latitude: float
    center_longitude: float
    default_zoom: int
    is_active: bool


class CitySummaryOut(BaseModel):
    city: CityOut
    total_problems: int
    critical_problems: int
    high_priority_problems: int
    resolved_problems: int
    unresolved_problems: int
    severity_breakdown: dict[str, int]
    status_breakdown: dict[str, int]
    problem_type_breakdown: dict[str, int]
    infrastructure_health_score: float  # 0 to 100, higher is healthier
    infrastructure_health_label: str
    has_demo_data: bool


# ---------- problems ----------
class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    latitude: float
    longitude: float
    road_name: str | None
    road_importance: str


class RiskComponentOut(BaseModel):
    raw: float
    weight: float
    contribution: float


class RiskScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score: float
    components: dict[str, RiskComponentOut]
    weights_version: str
    recommended_action: str
    reasons: list[str] = []


class ImageOut(BaseModel):
    id: int
    url: str
    source: str


class ProblemListItemOut(BaseModel):
    id: int
    problem_type: str
    severity: str
    status: str
    latitude: float
    longitude: float
    road_name: str | None
    recurrence_count: int
    is_demo: bool
    risk_score: float | None
    first_detected_at: datetime
    last_detected_at: datetime


class PaginatedProblems(BaseModel):
    items: list[ProblemListItemOut]
    total: int
    page: int
    page_size: int


class ProblemDetailOut(BaseModel):
    id: int
    problem_type: str
    severity: str
    status: str
    description: str | None
    recurrence_count: int
    is_demo: bool
    location: LocationOut
    risk: RiskScoreOut | None
    image: ImageOut | None
    confidence: float | None = None
    first_detected_at: datetime
    last_detected_at: datetime


class ProblemStatusUpdate(BaseModel):
    status: str


# ---------- detection / reporting ----------
class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectionOut(BaseModel):
    id: int | None = None
    problem_type: str
    confidence: float
    severity_suggested: str
    bbox: BoundingBox
    source: str = "model"
    low_confidence: bool = False


class AnalyzeImageResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    image_id: int
    model_available: bool
    model_version: str | None
    message: str | None = None
    image_width: int | None
    image_height: int | None
    detections: list[DetectionOut]


class DetectionVerifyRequest(BaseModel):
    action: str  # "confirm" or "reject"
    final_severity: str | None = None
    latitude: float
    longitude: float
    city_id: int
    road_name: str | None = None
    road_importance: str = "local"


class DetectionVerifyResponse(BaseModel):
    detection_id: int
    status: str
    problem_id: int | None = None


class ManualProblemRequest(BaseModel):
    problem_type: str
    severity: str
    latitude: float
    longitude: float
    city_id: int
    road_name: str | None = None
    road_importance: str = "local"
    image_id: int | None = None


class ManualProblemResponse(BaseModel):
    problem_id: int


class UserRegionRequest(BaseModel):
    """A box the user drew on the photo (values are fractions from 0 to 1)."""
    image_id: int
    problem_type: str
    severity: str
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def check_box(self):
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("Region must have a positive width and height.")
        if (self.x_max - self.x_min) < 0.01 or (self.y_max - self.y_min) < 0.01:
            raise ValueError("Region is too small - draw a larger area around the problem.")
        return self
