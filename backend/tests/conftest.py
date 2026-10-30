"""Test setup. The tests use their OWN database, because every test starts by wiping it.
"""
import os

# Your specific Neon test database connection string
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", 
    "postgresql+psycopg2://neondb_owner:npg_6o3MNFjgKPJz@ep-green-pine-b4y1pjm6-pooler.c-6.us-east-2.aws.neon.tech/nececity_test?sslmode=require"
)

# must be set BEFORE the app is imported, because the app reads it at import time
os.environ["DATABASE_URL"] = TEST_URL
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import City  # noqa: E402

# Safety check to ensure we never accidentally wipe your production database
if not engine.url.database.endswith("_test"):
    raise RuntimeError("Refusing to run: the test database name must end with '_test'.")


@pytest.fixture(scope="session")
def clean_database():
    # Dispose existing connections to prevent "table is locked" errors on Neon
    engine.dispose()  
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    # Clean up after all tests finish
    engine.dispose()
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(clean_database):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Wipe all data from all tables after every test to prevent UniqueViolation errors
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def client(clean_database):
    return TestClient(app)


@pytest.fixture
def city(db):
    c = City(name="Testville", slug="testville", state="West Bengal", center_latitude=26.7, center_longitude=88.4)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c