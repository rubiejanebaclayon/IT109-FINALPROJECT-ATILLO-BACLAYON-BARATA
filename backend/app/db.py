"""PostgreSQL access (Supabase) using psycopg 3 and a connection pool.

SQL INJECTION PREVENTION: every query in this project passes user values as
parameters (%s placeholders + a params tuple). User input is never formatted
into SQL strings. The only dynamic SQL fragments (ORDER BY, column names) come
from hard-coded whitelists in the routers.
"""
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import get_settings

_pool: ConnectionPool | None = None


def init_pool() -> None:
    global _pool
    settings = get_settings()
    # prepare_threshold=None is required when using Supabase's pooler (pgbouncer).
    _pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=8,
        kwargs={"row_factory": dict_row, "prepare_threshold": None},
        open=True,
    )


def close_pool() -> None:
    if _pool:
        _pool.close()


def _get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    return _pool


@contextmanager
def transaction() -> Iterator[Connection]:
    """Everything inside the `with` block commits together or rolls back together."""
    with _get_pool().connection() as conn:
        yield conn


def fetch_all(sql: str, params: Sequence[Any] = (), conn: Connection | None = None) -> list[dict]:
    if conn is not None:
        return conn.execute(sql, params).fetchall()
    with _get_pool().connection() as c:
        return c.execute(sql, params).fetchall()


def fetch_one(sql: str, params: Sequence[Any] = (), conn: Connection | None = None) -> dict | None:
    if conn is not None:
        return conn.execute(sql, params).fetchone()
    with _get_pool().connection() as c:
        return c.execute(sql, params).fetchone()


def execute(sql: str, params: Sequence[Any] = (), conn: Connection | None = None) -> int:
    if conn is not None:
        return conn.execute(sql, params).rowcount
    with _get_pool().connection() as c:
        return c.execute(sql, params).rowcount


def audit(actor_id, action: str, entity: str, entity_id=None, detail: dict | None = None,
          conn: Connection | None = None) -> None:
    from psycopg.types.json import Jsonb
    execute(
        "insert into audit_log (actor_id, action, entity, entity_id, detail) values (%s,%s,%s,%s,%s)",
        (actor_id, action, entity, str(entity_id) if entity_id else None, Jsonb(detail or {})),
        conn,
    )
