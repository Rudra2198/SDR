"""Context API errors (Plane 05, playbook Part 3)."""

from __future__ import annotations


class NotImplementedForTenant(Exception):
    """A real, registered layer that is not yet backed for this tenant.

    The three stubbed layers (knowledge graph, vector, document) raise this. The
    point (Part 3): the interface is complete and real, the stubs are registered,
    not missing. When a client needs the vector layer we implement it behind the
    stub and nothing upstream changes.
    """

    def __init__(self, layer: str, tenant_id: str, method: str) -> None:
        self.layer = str(layer)
        self.tenant_id = tenant_id
        self.method = method
        super().__init__(
            f"context layer '{self.layer}' (ctx.{method}) is not implemented for "
            f"tenant {tenant_id!r}"
        )
