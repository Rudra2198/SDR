"""Episodic layer (LIVE) — past traces and outcomes over Postgres JSONB.

`ctx.recall(task_type)` pulls recent episodes for a task type (e.g. past
``first_touch`` emails and how they landed) so a new draft can learn from what
worked. Backed by the ``episodic_memory`` table (Part 10).
"""

from __future__ import annotations

from typing import Any

from ruvu_sdr.db import get_cursor

DEFAULT_LIMIT = 5
SOURCE = "postgres:episodic_memory"


def recall(task_type: str, limit: int, tenant_id: str) -> tuple[list[dict[str, Any]], str]:
    """Most-recent episodes for ``task_type`` (newest first). Returns ``(data, source)``.

    ``tenant_id`` is carried for tracing/scoping; v1 is single-tenant so
    ``episodic_memory`` is not yet tenant-partitioned.
    """
    with get_cursor() as cur:
        cur.execute(
            "SELECT task_type, input_summary, output, outcome, created_at "
            "FROM episodic_memory WHERE task_type = %s "
            "ORDER BY created_at DESC LIMIT %s;",
            (task_type, limit),
        )
        rows = cur.fetchall()
    data = [
        {
            "task_type": row["task_type"],
            "input_summary": row["input_summary"],
            "output": row["output"],
            "outcome": row["outcome"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]
    return data, SOURCE
