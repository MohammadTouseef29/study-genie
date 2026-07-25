from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def _normalize_url(url: str) -> str:
    """Ensures the connection string routes through the psycopg3 driver,
    regardless of whether the raw Supabase-provided string uses the bare
    postgresql:// / postgres:// scheme."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add your Supabase Postgres connection string "
            "to .env (see .env.example)."
        )
    return _normalize_url(database_url)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
    return _engine
