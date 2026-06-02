"""Postgres access helpers (psycopg 3).

A thin layer over psycopg, no ORM. State is the source of truth and lives in
Postgres (playbook Parts 4 and 12); business logic stays in pure functions that
these helpers serve. Rows come back as dicts for ergonomic access.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from ruvu_sdr.config import get_settings


def connect() -> psycopg.Connection:
    """Open a new connection using DATABASE_URL. Caller owns the lifecycle."""
    return psycopg.connect(get_settings().database_url, row_factory=dict_row)


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Managed connection: commits on success, rolls back on error, always closes."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor() -> Iterator[psycopg.Cursor]:
    """Managed dict-row cursor over a managed connection."""
    with get_conn() as conn, conn.cursor() as cur:
        yield cur
