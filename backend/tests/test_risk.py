import pytest

from app.enums import RoadImportance, Severity
from app.risk import WEIGHTS, compute_risk


def test_weights_add_up_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_lowest_possible_problem():
    result = compute_risk(Severity.LOW, 1, 0, RoadImportance.LOCAL)
    # 0.40*0.25 + 0.25*0.2 + 0.20*0 + 0.15*0.3 = 0.195  ->  19.5
    assert result.score == 19.5
    assert "Low priority" in result.recommended_action


def test_worst_possible_problem_scores_100():
    result = compute_risk(Severity.CRITICAL, 5, 6, RoadImportance.HIGHWAY)
    assert result.score == 100.0
    assert "Immediate action" in result.recommended_action


def test_critical_scores_higher_than_low():
    low = compute_risk(Severity.LOW, 1, 0, RoadImportance.LOCAL).score
    critical = compute_risk(Severity.CRITICAL, 1, 0, RoadImportance.LOCAL).score
    assert critical > low


def test_components_add_up_to_the_score():
    result = compute_risk(Severity.HIGH, 3, 2, RoadImportance.ARTERIAL)
    total = sum(c["contribution"] for c in result.components.values())
    assert total == pytest.approx(result.score, abs=0.1)


def test_more_nearby_problems_raise_the_score_until_the_cap():
    scores = [compute_risk(Severity.MEDIUM, 1, n, RoadImportance.LOCAL).score for n in (0, 3, 6, 10)]
    assert scores[0] < scores[1] < scores[2]
    assert scores[2] == scores[3]  # 6 or more nearby problems gives the same (full) density value


def test_reasons_mention_recurrence_and_neighbours():
    result = compute_risk(Severity.CRITICAL, 4, 3, RoadImportance.HIGHWAY)
    text = " ".join(result.reasons)
    assert "Recurring" in text and "3 other" in text and "highway" in text


def test_plain_problem_gets_the_default_reason():
    result = compute_risk(Severity.LOW, 1, 0, RoadImportance.LOCAL)
    assert result.reasons == ["No elevated risk factors identified; routine-priority issue."]
