"""Semantic layer (LIVE) — typed metrics and dimensions over Postgres views.

`ctx.metric(name, slice)` resolves a named metric from a small registry, each
backed by a governed Postgres view (migration 002). v1 ships two metrics:
``contact_funnel`` (counts by lifecycle state) and ``reply_rate`` (replied / sent).
"""

from __future__ import annotations

from typing import Any

from ruvu_sdr.db import get_cursor

SOURCE_PREFIX = "postgres:"


def _contact_funnel(slice: str | None) -> tuple[dict[str, int], str]:
    """Contact counts by state. ``slice`` optionally filters to one state."""
    sql = "SELECT state, n FROM semantic_contact_funnel"
    params: tuple[Any, ...] = ()
    if slice not in (None, "all"):
        sql += " WHERE state = %s"
        params = (slice,)
    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    data = {row["state"]: int(row["n"]) for row in rows}
    return data, f"{SOURCE_PREFIX}semantic_contact_funnel"


def _reply_rate(slice: str | None) -> tuple[dict[str, float], str]:
    """Reply rate over all contacts. ``slice`` reserved for later segmentation."""
    if slice not in (None, "all"):
        raise ValueError(f"reply_rate has no slice {slice!r} yet (only 'all')")
    with get_cursor() as cur:
        cur.execute("SELECT replied, sent, value FROM semantic_reply_rate;")
        row = cur.fetchone()
    data = {
        "value": float(row["value"]),
        "replied": int(row["replied"]),
        "sent": int(row["sent"]),
    }
    return data, f"{SOURCE_PREFIX}semantic_reply_rate"


# name -> resolver. Add a metric here + its view in a migration; nothing else changes.
_METRICS = {
    "contact_funnel": _contact_funnel,
    "reply_rate": _reply_rate,
}

KNOWN_METRICS = tuple(_METRICS)


def metric(name: str, slice: str | None, tenant_id: str) -> tuple[Any, str]:
    """Resolve metric ``name`` (optionally sliced). Returns ``(data, source)``.

    ``tenant_id`` is carried for tracing/scoping; v1 is single-tenant so the views
    are not yet tenant-partitioned.
    """
    resolver = _METRICS.get(name)
    if resolver is None:
        raise ValueError(f"unknown metric {name!r} (known: {', '.join(KNOWN_METRICS)})")
    return resolver(slice)
