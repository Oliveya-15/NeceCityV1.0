"""Database connection. One engine for the whole app and one session per request."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

# NullPool and connect_timeout prevent Neon cold-start timeouts.
engine = create_engine(
    get_settings().DATABASE_URL, 
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 10},
    poolclass=NullPool
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Every table class inherits from this."""


def get_db():
    """FastAPI dependency: gives a session to a route and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback() # Prevents table locks
        db.close()