"""Risk score of a problem.

score = 100 x (0.40*severity + 0.25*recurrence + 0.20*density + 0.15*road importance)

Each factor is first turned into a number between 0 and 1 (its "raw" value).
The weights below are the only thing to change if you want a different formula.
"""
from dataclasses import dataclass

from app.enums import RoadImportance, Severity

WEIGHTS_VERSION = "v1"

WEIGHTS = {
    "severity": 0.40,
    "recurrence": 0.25,
    "density": 0.20,
    "road_importance": 0.15,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001, "risk weights must add up to 1"

DENSITY_RADIUS_M = 150          # "other problems nearby" means within this distance
DENSITY_FULL_AT = 6             # 6 or more nearby problems gives the full density value
RECURRENCE_FULL_AT = 5          # reported 5 or more times gives the full recurrence value

SEVERITY_RAW = {Severity.LOW: 0.25, Severity.MEDIUM: 0.50, Severity.HIGH: 0.75, Severity.CRITICAL: 1.00}
ROAD_RAW = {RoadImportance.LOCAL: 0.30, RoadImportance.ARTERIAL: 0.70, RoadImportance.HIGHWAY: 1.00}


@dataclass
class RiskResult:
    score: float
    components: dict
    reasons: list[str]
    recommended_action: str
    weights_version: str = WEIGHTS_VERSION


def recommended_action(score: float) -> str:
    if score >= 80:
        return "Immediate action required. Dispatch a repair crew within 24-48 hours."
    if score >= 60:
        return "High priority. Schedule repair within the next 7 days."
    if score >= 40:
        return "Moderate priority. Include in the next routine maintenance cycle (within 30 days)."
    return "Low priority. Monitor; address during periodic maintenance."


def compute_risk(
    severity: Severity,
    recurrence_count: int,
    nearby_count: int,
    road_importance: RoadImportance,
) -> RiskResult:
    """nearby_count = number of other unresolved problems within DENSITY_RADIUS_M."""
    raw = {
        "severity": SEVERITY_RAW[severity],
        "recurrence": min(recurrence_count / RECURRENCE_FULL_AT, 1.0),
        "density": min(nearby_count / DENSITY_FULL_AT, 1.0),
        "road_importance": ROAD_RAW[road_importance],
    }

    components = {}
    total = 0.0
    for factor, value in raw.items():
        contribution = round(value * WEIGHTS[factor] * 100, 2)
        components[factor] = {"raw": round(value, 2), "weight": WEIGHTS[factor], "contribution": contribution}
        total += contribution
    score = round(min(total, 100.0), 1)

    reasons = []
    if raw["severity"] >= 0.75:
        reasons.append(f"{severity.value.capitalize()} severity issue.")
    if recurrence_count >= 3:
        reasons.append(f"Recurring issue - detected {recurrence_count} times at this location.")
    if nearby_count >= 2:
        reasons.append(f"{nearby_count} other unresolved problems within {DENSITY_RADIUS_M}m.")
    if raw["road_importance"] >= 0.70:
        article = "an" if road_importance.value[0] in "aeiou" else "a"
        reasons.append(f"Located on {article} {road_importance.value} road.")
    if not reasons:
        reasons.append("No elevated risk factors identified; routine-priority issue.")

    return RiskResult(score=score, components=components, reasons=reasons, recommended_action=recommended_action(score))
