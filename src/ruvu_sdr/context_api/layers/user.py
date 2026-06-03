"""User / session layer (LIVE) — durable tenant preferences over Postgres.

`ctx.user_prefs()` returns the tenant's tone and brand rules (for Ruvu: warm,
relationship-first, no em-dashes) so every generated email is on-voice. Backed by
the ``tenant_prefs`` table (migration 002).
"""

from __future__ import annotations

from typing import Any

from ruvu_sdr.db import get_cursor

SOURCE = "postgres:tenant_prefs"


def user_prefs(tenant_id: str) -> tuple[dict[str, Any], str]:
    """Durable preferences for ``tenant_id``. Returns ``(data, source)``.

    Raises ``KeyError`` if the tenant has no prefs row (a configuration error, not
    a stubbed layer).
    """
    with get_cursor() as cur:
        cur.execute(
            "SELECT prefs FROM tenant_prefs WHERE tenant_id = %s;",
            (tenant_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"no prefs configured for tenant {tenant_id!r}")
    return row["prefs"], SOURCE
