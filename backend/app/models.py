"""Database tables (one Python class per table)."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import (
    DetectionStatus,
    ImageSource,
    ProblemStatus,
    ProblemType,
    RoadImportance,
    Severity,
)


def enum_column(enum_class):
    """Store an enum as plain text (its value) instead of a PostgreSQL enum type."""
    return Enum(enum_class, native_enum=False, length=30, values_callable=lambda e: [m.value for m in e])


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(120), default="West Bengal")
    center_latitude: Mapped[float] = mapped_column(Float)
    center_longitude: Mapped[float] = mapped_column(Float)
    default_zoom: Mapped[int] = mapped_column(default=13)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Location(Base):
    """A point on the map where a problem was seen."""
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    latitude: Mapped[float] = mapped_column(Float, index=True)
    longitude: Mapped[float] = mapped_column(Float, index=True)
    road_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    road_importance: Mapped[RoadImportance] = mapped_column(enum_column(RoadImportance), default=RoadImportance.LOCAL)


class Image(Base):
    """An uploaded photo. The file itself is on disk; only its details are stored here."""
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(50))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[ImageSource] = mapped_column(enum_column(ImageSource), default=ImageSource.UPLOAD)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    detections: Mapped[list["Detection"]] = relationship(back_populates="image", cascade="all, delete-orphan")


class Detection(Base):
    """One box found by the model (or drawn by the user) on a photo.
    It stays 'pending_review' until a person confirms or rejects it."""
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    problem_type: Mapped[ProblemType] = mapped_column(enum_column(ProblemType))
    confidence: Mapped[float] = mapped_column(Float)
    # box corners as fractions (0 to 1) of the image width / height
    bbox_x_min: Mapped[float] = mapped_column(Float)
    bbox_y_min: Mapped[float] = mapped_column(Float)
    bbox_x_max: Mapped[float] = mapped_column(Float)
    bbox_y_max: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(50))
    severity_suggested: Mapped[Severity] = mapped_column(enum_column(Severity))
    status: Mapped[DetectionStatus] = mapped_column(enum_column(DetectionStatus), default=DetectionStatus.PENDING_REVIEW)
    reviewed_severity: Mapped[Severity | None] = mapped_column(enum_column(Severity), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    image: Mapped["Image"] = relationship(back_populates="detections")
    problem: Mapped["Problem | None"] = relationship(back_populates="source_detection", uselist=False)


class Problem(Base):
    """A confirmed infrastructure problem. This is the main table of the app."""
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), index=True)
    source_detection_id: Mapped[int | None] = mapped_column(
        ForeignKey("detections.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    problem_type: Mapped[ProblemType] = mapped_column(enum_column(ProblemType))
    severity: Mapped[Severity] = mapped_column(enum_column(Severity))
    status: Mapped[ProblemStatus] = mapped_column(enum_column(ProblemStatus), default=ProblemStatus.DETECTED, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # how many times this problem has been reported at (nearly) the same spot
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    city: Mapped["City"] = relationship()
    location: Mapped["Location"] = relationship()
    source_detection: Mapped["Detection | None"] = relationship(back_populates="problem")
    risk_score: Mapped["RiskScore | None"] = relationship(
        back_populates="problem", cascade="all, delete-orphan", uselist=False
    )


class RiskScore(Base):
    """The risk score of a problem (0 to 100) with the reasons behind it."""
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), unique=True, index=True)
    score: Mapped[float] = mapped_column(Float)
    # how much each factor added to the score, saved as JSON so the page can show it
    components: Mapped[dict] = mapped_column(JSON)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    weights_version: Mapped[str] = mapped_column(String(20))
    recommended_action: Mapped[str] = mapped_column(String(300))
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    problem: Mapped["Problem"] = relationship(back_populates="risk_score")
