"""Fills the database with demo data (cities + sample problems).

Run from the backend folder:
    python -m app.seed            # adds the data (does nothing if problems already exist)
    python -m app.seed --reset    # deletes EVERYTHING first, then adds the data again

Every demo problem has is_demo = True, so the website can label it as demo data.
The random generator uses a fixed number (42), so you get the same data every time.
"""
import argparse
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.database import Base, SessionLocal, engine
from app.enums import ProblemStatus, ProblemType, RoadImportance, Severity
from app.models import City, Location, Problem
from app.services.problem_service import recompute_and_store_risk

RANDOM_SEED = 42

# name, state, latitude, longitude, map zoom
CITIES = [
    ("Siliguri", "West Bengal", 26.7271, 88.3953, 13),
    ("Kolkata", "West Bengal", 22.5726, 88.3639, 12),
    ("Asansol", "West Bengal", 23.6739, 86.9524, 13),
    ("Durgapur", "West Bengal", 23.5204, 87.3119, 13),
    ("Howrah", "West Bengal", 22.5958, 88.2636, 13),
    ("Kharagpur", "West Bengal", 22.3460, 87.2320, 13),
    ("Bardhaman", "West Bengal", 23.2324, 87.8615, 13),
    ("Jalpaiguri", "West Bengal", 26.5416, 88.7195, 13),
]

# how often each value should appear in the demo data (higher number = more common)
TYPE_WEIGHTS = {
    ProblemType.POTHOLE: 30, ProblemType.ROAD_DAMAGE: 20, ProblemType.GARBAGE: 20,
    ProblemType.WATERLOGGING: 12, ProblemType.OPEN_DRAIN: 10, ProblemType.DAMAGED_ROAD_SIGN: 8,
}
SEVERITY_WEIGHTS = {Severity.LOW: 25, Severity.MEDIUM: 35, Severity.HIGH: 25, Severity.CRITICAL: 15}
STATUS_WEIGHTS = {
    ProblemStatus.DETECTED: 35, ProblemStatus.VERIFIED: 20, ProblemStatus.IN_PROGRESS: 15, ProblemStatus.RESOLVED: 30,
}
ROAD_WEIGHTS = {RoadImportance.LOCAL: 55, RoadImportance.ARTERIAL: 35, RoadImportance.HIGHWAY: 10}
ROAD_NAMES = ["MG Road", "Station Road", "Hill Cart Road", "Sevoke Road", "Bypass Road", "Ward Lane"]


def pick(rng: random.Random, weights: dict):
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def random_point(rng: random.Random, lat: float, lon: float, radius_km: float = 6.0):
    """A random point inside a small square around the city centre."""
    return (
        round(lat + rng.uniform(-1, 1) * radius_km / 111.0, 6),
        round(lon + rng.uniform(-1, 1) * radius_km / (111.0 * 0.9), 6),
    )


def jitter(rng: random.Random, lat: float, lon: float, metres: float):
    """Move a point by up to `metres` in each direction."""
    return (
        round(lat + rng.uniform(-metres, metres) / 111_000, 6),
        round(lon + rng.uniform(-metres, metres) / (111_000 * 0.9), 6),
    )


def add_cities(db: Session) -> dict[str, City]:
    cities = {}
    for name, state, lat, lon, zoom in CITIES:
        slug = name.lower()
        city = db.query(City).filter_by(slug=slug).one_or_none()
        if city is None:
            city = City(name=name, slug=slug, state=state, center_latitude=lat, center_longitude=lon, default_zoom=zoom)
            db.add(city)
        cities[slug] = city
    db.flush()
    return cities


def add_problems(db: Session, rng: random.Random, city: City, count: int) -> None:
    now = datetime.utcnow()
    # a few "problem areas" where many reports cluster, like a junction that floods every year
    hotspots = [random_point(rng, city.center_latitude, city.center_longitude, 4.0) for _ in range(5)]

    for number in range(count):
        near_hotspot = rng.random() < 0.30
        if near_hotspot:
            centre = rng.choice(hotspots)
            lat, lon = jitter(rng, centre[0], centre[1], 60)
        else:
            lat, lon = random_point(rng, city.center_latitude, city.center_longitude)

        location = Location(
            city_id=city.id, latitude=lat, longitude=lon,
            road_name=f"{rng.choice(ROAD_NAMES)} #{number + 1}",
            road_importance=pick(rng, ROAD_WEIGHTS),
        )
        db.add(location)
        db.flush()

        status = pick(rng, STATUS_WEIGHTS)
        first_seen = now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23))
        recurrence = rng.choice([2, 3, 4, 5]) if near_hotspot and rng.random() < 0.5 else 1

        problem = Problem(
            city_id=city.id, location_id=location.id,
            problem_type=pick(rng, TYPE_WEIGHTS), severity=pick(rng, SEVERITY_WEIGHTS), status=status,
            recurrence_count=recurrence, is_demo=True,
            first_detected_at=first_seen, last_detected_at=first_seen,
        )
        db.add(problem)
        db.flush()
        recompute_and_store_risk(db, problem)


def run(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(engine)
        print("All tables dropped.")
    Base.metadata.create_all(engine)

    rng = random.Random(RANDOM_SEED)
    db = SessionLocal()
    try:
        cities = add_cities(db)
        db.commit()

        if db.query(Problem).count() > 0:
            print("Problems already exist - nothing added. Use --reset to start again.")
            return

        add_problems(db, rng, cities["siliguri"], 55)
        add_problems(db, rng, cities["kolkata"], 45)
        db.commit()
        print(f"Done: {db.query(City).count()} cities and {db.query(Problem).count()} demo problems added.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add demo data to the NeceCity database.")
    parser.add_argument("--reset", action="store_true", help="delete everything first")
    run(reset=parser.parse_args().reset)
