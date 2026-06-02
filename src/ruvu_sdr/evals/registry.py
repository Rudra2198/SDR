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
