"""Eval registry (playbook Part 6): which evals exist, and which gate which phase.

The same harness runs two schedules (Part 6):
- ``pr``      — fast-and-narrow, runs on every PR (Customer 01: "safe to merge").
- ``nightly`` — slow-and-broad, runs the full registered suite (Customer 02).

Phase 0 registers nothing. Evals are added as phases reach them: ``email_quality``
in Phase 2, ``reply_intent`` and ``injection_suite`` in Phase 4, and so on.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ruvu_sdr.evals.models import Dimension
from ruvu_sdr.evals.scorers import Scorer

# The code under test: maps a case input to an output to be scored.
Target = Callable[[Any], Any]


@dataclass(frozen=True)
class EvalSpec:
    """Declares one eval: its dimension, the build phase it gates, scorer, target."""

    name: str
    dimension: Dimension
    gates_phase: str  # e.g. "phase-2" — the build phase this eval gates
    scorer: Scorer
    target: Target
    description: str = ""


# All registered evals, keyed by name. Empty in Phase 0.
REGISTRY: dict[str, EvalSpec] = {}

# Explicit fast subset that runs on every PR. References names in REGISTRY.
PR_SUITE: list[str] = []

AVAILABLE_SUITES = ("pr", "nightly")


def register(spec: EvalSpec) -> None:
    """Register an eval. Raises if the name is already taken."""
    if spec.name in REGISTRY:
        raise ValueError(f"eval already registered: {spec.name!r}")
    REGISTRY[spec.name] = spec


def suite_specs(suite: str) -> list[EvalSpec]:
    """Return the eval specs for a suite.

    ``pr`` is the explicit fast subset; ``nightly`` is every registered eval.
    """
    if suite == "pr":
        return [REGISTRY[name] for name in PR_SUITE]
    if suite == "nightly":
        return list(REGISTRY.values())
    raise KeyError(f"unknown suite: {suite!r} (known: {', '.join(AVAILABLE_SUITES)})")


# ─── Registered evals ─────────────────────────────────────────────────────────
# Phase 1: the Context API contract (unit). The first eval with real cases, so the
# PR gate stops passing vacuously. Imports live here (not at top) so registration
# is a clear, ordered side effect of importing this module.
def _register_phase_1() -> None:
    from ruvu_sdr.context_api.contract import context_contract_target
    from ruvu_sdr.evals.scorers import ContextContractScorer

    register(
        EvalSpec(
            name="context_api_contract",
            dimension=Dimension.UNIT,
            gates_phase="phase-1",
            scorer=ContextContractScorer(),
            target=context_contract_target,
            description=(
                "Context API surface (Part 3): live methods return the "
                "ContextResult envelope; stubbed layers raise NotImplementedForTenant."
            ),
        )
    )
    PR_SUITE.append("context_api_contract")


# Phase 1: the hubspot-mcp tool contract (unit). Encodes the locked tool surface
# (read_contacts / read_company / log_activity) as a gate before the tools work —
# eval-first (Part 5). Red until step 5 implements the tools.
def _register_phase_1_hubspot() -> None:
    from ruvu_sdr.evals.scorers import HubSpotContractScorer
    from ruvu_sdr.mcp_servers.hubspot.contract import hubspot_contract_target

    register(
        EvalSpec(
            name="hubspot_tool_contract",
            dimension=Dimension.UNIT,
            gates_phase="phase-1",
            scorer=HubSpotContractScorer(),
            target=hubspot_contract_target,
            description=(
                "hubspot-mcp tool surface (Part 8): read tools return shapes "
                "normalized to the Part 10 schema, read_company 404 -> None, "
                "errors surface HubSpotError."
            ),
        )
    )
    PR_SUITE.append("hubspot_tool_contract")


_register_phase_1()
_register_phase_1_hubspot()
