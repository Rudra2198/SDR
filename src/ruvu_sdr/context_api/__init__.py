"""Plane 05 — the Context API (the moat).

One tenant-scoped interface over six layers (semantic, knowledge graph, vector,
document, episodic, user/session). Three live, three stubbed behind the same
interface. See `api.ContextAPI` and playbook Part 3.
"""

from ruvu_sdr.context_api.api import DEFAULT_TENANT, ContextAPI
from ruvu_sdr.context_api.errors import NotImplementedForTenant
from ruvu_sdr.context_api.models import ContextResult, Layer

__all__ = [
    "ContextAPI",
    "ContextResult",
    "DEFAULT_TENANT",
    "Layer",
    "NotImplementedForTenant",
]
