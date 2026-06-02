"""Scorers / judges (playbook Part 6).

Deterministic checks plus LLM-as-judge where needed (the LLM judges arrive with
the email-quality and reply-intent evals in later phases). Every scorer obeys the
same contract: given `expected` and `output`, return a `ScoreResult`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ruvu_sdr.evals.models import ScoreResult


class Scorer(ABC):
    """Scores one (expected, output) pair."""

    name: str = "scorer"

    @abstractmethod
    def score(self, *, expected: Any, output: Any) -> ScoreResult:
        """Return a normalized verdict for this output against its expectation."""


class ExactMatchScorer(Scorer):
    """Trivial deterministic scorer: pass iff ``output == expected``.

    Exists to prove the Scorer interface end to end in Phase 0. Real evals
    register richer scorers (rubric-based LLM judges, etc.) in later phases.
    """

    name = "exact_match"

    def score(self, *, expected: Any, output: Any) -> ScoreResult:
        ok = output == expected
        return ScoreResult(
            passed=ok,
            score=1.0 if ok else 0.0,
            detail="" if ok else f"expected {expected!r}, got {output!r}",
        )
