from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./inventory.db"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _engine_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def create_db_engine(database_url: str | None = None):
    resolved_url = database_url or get_database_url()
    return create_engine(resolved_url, future=True, **_engine_args(resolved_url))


def create_session_factory(database_url: str | None = None):
    engine = create_db_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


SessionLocal = create_session_factory()


@contextmanager
def get_session(database_url: str | None = None) -> Generator[Session, None, None]:
    session_factory = SessionLocal if database_url is None else create_session_factory(database_url)
    db = session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
