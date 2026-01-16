"""Database setup and session management helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


def build_engine(db_path: Path) -> Engine:
    """Create a SQLAlchemy engine for the SQLite database path."""
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory bound to the engine."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine, models: Iterable[type]) -> None:
    """Create database tables for the provided SQLAlchemy model classes."""
    for model in models:
        model.metadata.create_all(bind=engine)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Provide a transactional scope for database operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
