"""The fixed lists of values used everywhere (database, ML, risk score, frontend)."""
import enum


class ProblemType(str, enum.Enum):
    POTHOLE = "pothole"
    ROAD_DAMAGE = "road_damage"
    GARBAGE = "garbage"
    WATERLOGGING = "waterlogging"
    DAMAGED_ROAD_SIGN = "damaged_road_sign"
    OPEN_DRAIN = "open_drain"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProblemStatus(str, enum.Enum):
    DETECTED = "detected"
    VERIFIED = "verified"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class DetectionStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class RoadImportance(str, enum.Enum):
    LOCAL = "local"        # small residential street
    ARTERIAL = "arterial"  # main city road
    HIGHWAY = "highway"    # state or national highway


class ImageSource(str, enum.Enum):
    UPLOAD = "upload"
    DEMO = "demo"


# the order a problem moves through; used to block jumps like Detected -> Resolved
STATUS_ORDER = [
    ProblemStatus.DETECTED,
    ProblemStatus.VERIFIED,
    ProblemStatus.IN_PROGRESS,
    ProblemStatus.RESOLVED,
]
