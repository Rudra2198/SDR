"""Shared shapes for the Context API (Plane 05, playbook Part 3).

Every live method returns the same envelope (`ContextResult`) regardless of which
underlying store served it. "Same shape, N tenants, pluggable layers": this is what
lets us swap a stubbed layer for a real one later without touching agent code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Layer(StrEnum):
    """The six context layers (Part 3). Three live, three stubbed in v1."""

    SEMANTIC = "semantic"  # LIVE   — typed metrics / dimensions (Postgres views)
    GRAPH = "graph"  # STUBBED — knowledge graph
    VECTOR = "vector"  # STUBBED — embedded chunks
    DOCUMENT = "document"  # STUBBED — raw originals
    EPISODIC = "episodic"  # LIVE   — past traces and outcomes (Postgres JSONB)
    USER = "user"  # LIVE   — durable preferences (Postgres)


@dataclass(frozen=True)
class ContextResult:
    """The one shape every live Context API method returns.

    Attributes:
        layer: which of the six layers served this (a `Layer` value).
        tenant_id: the tenant this read was scoped to.
        query: what was asked (method args), echoed back for traceability.
        data: the payload, shaped by the layer (a metric dict, a list of
            episodes, a prefs dict, ...).
        source: identifier of the backing store, e.g. ``postgres:semantic_reply_rate``.
    """

    layer: Layer
    tenant_id: str
    query: dict[str, Any]
    data: Any
    source: str
