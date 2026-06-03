"""The Context API (Plane 05, the moat — playbook Part 3).

ONE tenant-scoped interface over six layers, a fixed return shape, every method
traced. Agents never touch a data store directly for context (Part 4 rule 3); they
call this. Three layers are LIVE (semantic, episodic, user); three are STUBBED and
raise `NotImplementedForTenant` (knowledge graph, vector, document). The stubs are
registered and real, not missing: when a client needs one we implement it behind
the stub and nothing upstream changes.

    ctx = ContextAPI()                       # defaults to tenant 'ruvu'
    ctx.metric("contact_funnel")             # semantic — LIVE
    ctx.recall("first_touch")                # episodic — LIVE
    ctx.user_prefs()                         # user     — LIVE
    ctx.graph_path(a, b)                     # graph    — raises NotImplementedForTenant
    ctx.search(query, k=5)                   # vector   — raises NotImplementedForTenant
    ctx.doc(uri)                             # document — raises NotImplementedForTenant
"""

from __future__ import annotations

from typing import Any

from ruvu_sdr.context_api.errors import NotImplementedForTenant
from ruvu_sdr.context_api.layers import episodic, semantic, user
from ruvu_sdr.context_api.models import ContextResult, Layer
from ruvu_sdr.observability import observe, tag_observation

DEFAULT_TENANT = "ruvu"


class ContextAPI:
    """One tenant-scoped interface over the six context layers (Part 3)."""

    def __init__(self, tenant_id: str = DEFAULT_TENANT) -> None:
        self.tenant_id = tenant_id

    # ─── Live layers ──────────────────────────────────────────────────────────
    @observe(name="ctx.metric")
    def metric(self, name: str, slice: str | None = None) -> ContextResult:
        """Semantic layer: a typed metric, optionally sliced by a dimension."""
        tag_observation(tenant_id=self.tenant_id, layer=Layer.SEMANTIC, metric=name)
        data, source = semantic.metric(name, slice, self.tenant_id)
        return ContextResult(
            layer=Layer.SEMANTIC,
            tenant_id=self.tenant_id,
            query={"name": name, "slice": slice},
            data=data,
            source=source,
        )

    @observe(name="ctx.recall")
    def recall(self, task_type: str, limit: int = episodic.DEFAULT_LIMIT) -> ContextResult:
        """Episodic layer: recent past episodes for a task type (newest first)."""
        tag_observation(tenant_id=self.tenant_id, layer=Layer.EPISODIC, task_type=task_type)
        data, source = episodic.recall(task_type, limit, self.tenant_id)
        return ContextResult(
            layer=Layer.EPISODIC,
            tenant_id=self.tenant_id,
            query={"task_type": task_type, "limit": limit},
            data=data,
            source=source,
        )

    @observe(name="ctx.user_prefs")
    def user_prefs(self) -> ContextResult:
        """User/session layer: the tenant's durable tone and brand rules."""
        tag_observation(tenant_id=self.tenant_id, layer=Layer.USER)
        data, source = user.user_prefs(self.tenant_id)
        return ContextResult(
            layer=Layer.USER,
            tenant_id=self.tenant_id,
            query={},
            data=data,
            source=source,
        )

    # ─── Stubbed layers — registered and real, raise NotImplementedForTenant ──
    @observe(name="ctx.graph_path")
    def graph_path(self, a: Any, b: Any) -> ContextResult:
        """Knowledge graph layer (STUBBED)."""
        tag_observation(tenant_id=self.tenant_id, layer=Layer.GRAPH, stubbed=True)
        raise NotImplementedForTenant(Layer.GRAPH, self.tenant_id, "graph_path")

    @observe(name="ctx.search")
    def search(self, query: str, k: int = 5) -> ContextResult:
        """Vector store layer (STUBBED)."""
        tag_observation(tenant_id=self.tenant_id, layer=Layer.VECTOR, stubbed=True)
        raise NotImplementedForTenant(Layer.VECTOR, self.tenant_id, "search")

    @observe(name="ctx.doc")
    def doc(self, uri: str) -> ContextResult:
        """Document store layer (STUBBED)."""
        tag_observation(tenant_id=self.tenant_id, layer=Layer.DOCUMENT, stubbed=True)
        raise NotImplementedForTenant(Layer.DOCUMENT, self.tenant_id, "doc")
