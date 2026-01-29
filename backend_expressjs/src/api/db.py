import os
from contextlib import contextmanager
from typing import Generator, Optional

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

# SQLAlchemy engine + session factory. We keep it simple and synchronous for compatibility
# and to minimize operational complexity in this template.
#
# IMPORTANT:
# This service must be able to start and serve /api/health even when DATABASE_URL is not
# provided by the platform environment (e.g., in CI or preview deployments). Therefore we
# do NOT raise at import time. Instead, endpoints that require a DB will return 503.
DATABASE_URL = os.getenv("DATABASE_URL")

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _init_engine() -> None:
    """Initialize engine + session factory if DATABASE_URL is configured."""
    global _engine, _SessionLocal
    if _engine is not None and _SessionLocal is not None:
        return
    if not DATABASE_URL:
        return
    _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


# PUBLIC_INTERFACE
def get_engine() -> Optional[Engine]:
    """Return the SQLAlchemy Engine if DATABASE_URL is configured; otherwise None."""
    _init_engine()
    return _engine


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy DB session and always closes it.

    Raises:
        HTTPException(503): If DATABASE_URL is not configured.
    """
    _init_engine()
    if _SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured (DATABASE_URL missing).",
        )

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for scripts (seed/migrations helpers) to acquire a DB session.

    Raises:
        RuntimeError: If DATABASE_URL is not configured (scripts require DB).
    """
    _init_engine()
    if _SessionLocal is None:
        raise RuntimeError(
            "Database is not configured (DATABASE_URL missing). "
            "Set DATABASE_URL to use db_session()."
        )

    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
