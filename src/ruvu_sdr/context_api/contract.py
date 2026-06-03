"""Contract-eval target for the Context API (playbook Parts 3, 6).

The unit eval that gates this slice: invoke a Context API method described by a case
and normalize the result into a small, scorable shape. Live methods must return the
`ContextResult` envelope; stubbed methods must raise `NotImplementedForTenant`.

A case input is ``{"method": <name>, "args": {...}}``. The normalized output is either
``{"kind": "shape", "layer": <layer>, "keys": [...]}`` for a live method, or
``{"kind": "raises", "error": "NotImplementedForTenant"}`` for a stub. Any other
exception propagates, so a genuinely broken live method fails the run loudly rather
than being silently scored.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from ruvu_sdr.context_api.api import ContextAPI
from ruvu_sdr.context_api.errors import NotImplementedForTenant
from ruvu_sdr.context_api.models import ContextResult

_ENVELOPE_KEYS = sorted(f.name for f in fields(ContextResult))


def context_contract_target(case_input: dict[str, Any]) -> dict[str, Any]:
    """Run one Context API method and normalize its result for scoring."""
    ctx = ContextAPI(tenant_id=case_input.get("tenant_id", "ruvu"))
    method = getattr(ctx, case_input["method"])
    args = case_input.get("args", {})
    try:
        result = method(**args)
    except NotImplementedForTenant:
        return {"kind": "raises", "error": "NotImplementedForTenant"}

    assert isinstance(result, ContextResult)
    return {
        "kind": "shape",
        "layer": str(result.layer),
        "keys": sorted(result.__dict__.keys()),
    }


# Exposed so the golden set's "shape" cases can assert the full envelope is present.
ENVELOPE_KEYS = _ENVELOPE_KEYS
