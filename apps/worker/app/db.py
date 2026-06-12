"""Database access via a psycopg connection pool."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import get_settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_settings().database_url,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"row_factory": dict_row},
        )
    return _pool


def close_pool() -> None:
    """Close the pool explicitly (avoids noisy finalizer warnings in short-lived scripts)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def cursor() -> Iterator[Any]:
    """Yield a cursor inside a transaction; commit on success, rollback on error."""
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            yield cur


def ping() -> bool:
    """Return True if the database answers a trivial query."""
    with cursor() as cur:
        cur.execute("select 1 as ok")
        row = cur.fetchone()
        return bool(row and row["ok"] == 1)


def to_vector(values: list[float]) -> str:
    """Render a float list as a pgvector literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(float(v)) for v in values) + "]"
