"""
Database configuration for the application.
This module defines the SQLAlchemy engine, session, and base class for the models.
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.infrastructure.config.settings import settings

# Create SQLAlchemy engine

connect_args: Dict[str, Any] = {}
engine_args: Dict[str, Any] = {
    "pool_pre_ping": True,
    "echo": settings.SQL_ECHO,
}

if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False
    engine_args["connect_args"] = connect_args
else:
    engine_args["pool_size"] = settings.DB_POOL_SIZE
    engine_args["max_overflow"] = settings.DB_MAX_OVERFLOW

# Create SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL, **engine_args)


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.

    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all tables in the database."""
    Base.metadata.drop_all(bind=engine)
