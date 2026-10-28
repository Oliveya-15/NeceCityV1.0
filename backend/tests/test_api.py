"""Tests of the API: they call the real routes and use a real PostgreSQL test database."""
import io

from PIL import Image


def manual_problem(client, city, **overrides):
    body = {
        "problem_type": "pothole", "severity": "high", "latitude": 26.7271, "longitude": 88.3953,
        "city_id": city.id, "road_name": "Test Road", "road_importance": "arterial",
    }
    body.update(overrides)
    return client.post("/api/v1/problems/manual", json=body)


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cities_list(client, city):
    response = client.get("/api/v1/cities")
    assert response.status_code == 200
    assert [c["slug"] for c in response.json()] == ["testville"]


def test_summary_of_unknown_city_is_404(client):
    assert client.get("/api/v1/cities/999/summary").status_code == 404


def test_summary_counts_problems(client, city):
    manual_problem(client, city, severity="critical")
    manual_problem(client, city, problem_type="garbage", severity="low", latitude=26.75, longitude=88.40)
    summary = client.get(f"/api/v1/cities/{city.id}/summary").json()
    assert summary["total_problems"] == 2
    assert summary["critical_problems"] == 1
    assert summary["severity_breakdown"]["low"] == 1
    assert summary["problem_type_breakdown"]["garbage"] == 1


def test_manual_problem_is_saved_with_a_risk_score(client, city):
    problem_id = manual_problem(client, city).json()["problem_id"]
    detail = client.get(f"/api/v1/problems/{problem_id}").json()
    assert detail["status"] == "verified"
    assert detail["risk"]["score"] > 0
    assert set(detail["risk"]["components"]) == {"severity", "recurrence", "density", "road_importance"}


def test_invalid_problem_type_is_rejected(client, city):
    assert manual_problem(client, city, problem_type="spaceship").status_code == 422


def test_same_type_within_30_metres_is_merged(client, city):
    first = manual_problem(client, city).json()["problem_id"]
    # about 11 m further north: same problem, so the recurrence count goes up
    second = manual_problem(client, city, latitude=26.7272, severity="critical").json()["problem_id"]
    assert first == second
    detail = client.get(f"/api/v1/problems/{first}").json()
    assert detail["recurrence_count"] == 2
    assert detail["severity"] == "critical"  # the higher severity is kept


def test_same_type_far_away_is_a_new_problem(client, city):
    first = manual_problem(client, city).json()["problem_id"]
    # about 110 m away: a different problem
    second = manual_problem(client, city, latitude=26.7281).json()["problem_id"]
    assert first != second


def test_different_type_at_same_spot_is_a_new_problem(client, city):
    first = manual_problem(client, city).json()["problem_id"]
    second = manual_problem(client, city, problem_type="garbage").json()["problem_id"]
    assert first != second


def test_nearby_problems_increase_the_risk_score(client, city):
    # a problem on its own
    alone = manual_problem(client, city, problem_type="garbage", severity="low").json()["problem_id"]
    alone_score = client.get(f"/api/v1/problems/{alone}").json()["risk"]["score"]

    # two other problems of different types within 150 m of the same spot
    manual_problem(client, city, problem_type="pothole", latitude=26.7276)
    manual_problem(client, city, problem_type="open_drain", latitude=26.7266)

    # saving the same kind of problem again recalculates its score with the new neighbours
    again = manual_problem(client, city, problem_type="garbage", severity="low").json()["problem_id"]
    assert again == alone
    risk = client.get(f"/api/v1/problems/{alone}").json()["risk"]
    assert risk["score"] > alone_score
    assert any("2 other unresolved problems" in reason for reason in risk["reasons"])


def test_status_must_move_one_step_at_a_time(client, city):
    problem_id = manual_problem(client, city).json()["problem_id"]  # starts as "verified"
    jump = client.patch(f"/api/v1/problems/{problem_id}/status", json={"status": "resolved"})
    assert jump.status_code == 409
    step = client.patch(f"/api/v1/problems/{problem_id}/status", json={"status": "in_progress"})
    assert step.status_code == 200
    assert step.json()["status"] == "in_progress"


def test_unknown_status_is_422(client, city):
    problem_id = manual_problem(client, city).json()["problem_id"]
    assert client.patch(f"/api/v1/problems/{problem_id}/status", json={"status": "flying"}).status_code == 422


def test_priorities_are_sorted_by_risk(client, city):
    manual_problem(client, city, problem_type="garbage", severity="low", road_importance="local")
    manual_problem(client, city, problem_type="pothole", severity="critical", road_importance="highway",
                   latitude=26.80, longitude=88.50)
    scores = [p["risk_score"] for p in client.get(f"/api/v1/priorities?city_id={city.id}").json()]
    assert scores == sorted(scores, reverse=True)
    assert len(scores) == 2


def test_resolved_problems_are_hidden_from_priorities_by_default(client, city):
    problem_id = manual_problem(client, city).json()["problem_id"]
    for status in ("in_progress", "resolved"):
        client.patch(f"/api/v1/problems/{problem_id}/status", json={"status": status})
    assert client.get(f"/api/v1/priorities?city_id={city.id}").json() == []
    shown = client.get(f"/api/v1/priorities?city_id={city.id}&unresolved_only=false").json()
    assert len(shown) == 1


def test_map_filters(client, city):
    manual_problem(client, city, problem_type="pothole", severity="high")
    manual_problem(client, city, problem_type="garbage", severity="low", latitude=26.80, longitude=88.50)
    everything = client.get(f"/api/v1/map/problems?city_id={city.id}").json()
    only_garbage = client.get(f"/api/v1/map/problems?city_id={city.id}&problem_type=garbage").json()
    only_high = client.get(f"/api/v1/map/problems?city_id={city.id}&severity=high").json()
    assert len(everything) == 2
    assert [p["problem_type"] for p in only_garbage] == ["garbage"]
    assert [p["severity"] for p in only_high] == ["high"]


def test_problem_list_is_filtered_by_city(client, city, db):
    from app.models import City
    other = City(name="Other", slug="other", state="WB", center_latitude=22.5, center_longitude=88.3)
    db.add(other)
    db.commit()
    manual_problem(client, city)
    manual_problem(client, other)
    items = client.get(f"/api/v1/problems?city_id={city.id}").json()["items"]
    assert len(items) == 1


def make_png(width=200, height=150) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 120, 120)).save(buffer, "PNG")
    return buffer.getvalue()


def test_upload_without_a_model_still_works(client):
    # in the test setup the ONNX file does not exist, so the app must say "model not available"
    response = client.post("/api/v1/analyze/image", files={"file": ("street.png", make_png(), "image/png")})
    assert response.status_code == 200
    body = response.json()
    assert body["image_id"] > 0
    assert body["detections"] == []


def test_upload_of_a_pdf_is_rejected(client):
    response = client.post("/api/v1/analyze/image", files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]


def test_drawn_region_can_be_confirmed_into_a_problem(client, city):
    image_id = client.post("/api/v1/analyze/image", files={"file": ("s.png", make_png(), "image/png")}).json()["image_id"]
    region = client.post("/api/v1/detections/user-region", json={
        "image_id": image_id, "problem_type": "pothole", "severity": "medium",
        "x_min": 0.2, "y_min": 0.2, "x_max": 0.5, "y_max": 0.5,
    })
    assert region.status_code == 200
    detection_id = region.json()["id"]

    verify = client.post(f"/api/v1/detections/{detection_id}/verify", json={
        "action": "confirm", "final_severity": "high", "latitude": 26.7271, "longitude": 88.3953, "city_id": city.id,
    })
    assert verify.status_code == 200
    problem_id = verify.json()["problem_id"]
    assert client.get(f"/api/v1/problems/{problem_id}").json()["severity"] == "high"

    # a detection can only be reviewed once
    again = client.post(f"/api/v1/detections/{detection_id}/verify", json={
        "action": "confirm", "latitude": 26.7271, "longitude": 88.3953, "city_id": city.id,
    })
    assert again.status_code == 409


def test_rejected_detection_creates_no_problem(client, city):
    image_id = client.post("/api/v1/analyze/image", files={"file": ("s.png", make_png(), "image/png")}).json()["image_id"]
    detection_id = client.post("/api/v1/detections/user-region", json={
        "image_id": image_id, "problem_type": "garbage", "severity": "low",
        "x_min": 0.1, "y_min": 0.1, "x_max": 0.4, "y_max": 0.4,
    }).json()["id"]
    result = client.post(f"/api/v1/detections/{detection_id}/verify", json={
        "action": "reject", "latitude": 0, "longitude": 0, "city_id": city.id,
    }).json()
    assert result["status"] == "rejected" and result["problem_id"] is None
    assert client.get(f"/api/v1/problems?city_id={city.id}").json()["total"] == 0


def test_region_that_is_too_small_is_rejected(client):
    image_id = client.post("/api/v1/analyze/image", files={"file": ("s.png", make_png(), "image/png")}).json()["image_id"]
    response = client.post("/api/v1/detections/user-region", json={
        "image_id": image_id, "problem_type": "pothole", "severity": "low",
        "x_min": 0.5, "y_min": 0.5, "x_max": 0.505, "y_max": 0.505,
    })
    assert response.status_code == 422
