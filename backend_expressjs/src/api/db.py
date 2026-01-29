import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# SQLAlchemy engine + session factory. We keep it simple and synchronous for compatibility
# and to minimize operational complexity in this template.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # NOTE: This is intentionally a hard error so misconfiguration is obvious in CI/runtime.
    raise RuntimeError(
        "DATABASE_URL is not set. Please configure it in the backend_expressjs .env "
        "(see .env.example). Expected format: postgresql+psycopg://user:pass@host:5432/db"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for scripts (seed/migrations helpers) to acquire a DB session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
