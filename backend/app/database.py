"""Database connection. One engine for the whole app and one session per request."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Every table class inherits from this."""


def get_db():
    """FastAPI dependency: gives a session to a route and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
