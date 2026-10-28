"""Test setup. The tests use their OWN database, because every test starts by wiping it.

Create it once:   createdb nececity_test   (or in psql: CREATE DATABASE nececity_test;)
Use another one:  set TEST_DATABASE_URL before running pytest.
"""
import os

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/nececity_test"
)
# must be set BEFORE the app is imported, because the app reads it at import time
os.environ["DATABASE_URL"] = TEST_URL
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import City  # noqa: E402

if not engine.url.database.endswith("_test"):
    raise RuntimeError("Refusing to run: the test database name must end with '_test'.")


@pytest.fixture
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db(clean_database):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(clean_database):
    # no "with" block on purpose: the startup code (loading the model) is not needed here
    return TestClient(app)


@pytest.fixture
def city(db):
    c = City(name="Testville", slug="testville", state="West Bengal", center_latitude=26.7, center_longitude=88.4)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
