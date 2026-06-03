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


class ContextContractScorer(Scorer):
    """Scores the Context API contract eval (Phase 1, unit dimension).

    Two case kinds (see `context_api.contract`):
    - ``shape``  — a live method must return the envelope: the right ``layer`` and
      at least the expected envelope keys.
    - ``raises`` — a stubbed method must raise ``NotImplementedForTenant``.
    """

    name = "context_contract"

    def score(self, *, expected: Any, output: Any) -> ScoreResult:
        if output.get("kind") != expected.get("kind"):
            return ScoreResult(
                passed=False,
                score=0.0,
                detail=f"kind: expected {expected.get('kind')!r}, got {output.get('kind')!r}",
            )

        kind = expected["kind"]
        if kind == "raises":
            ok = output.get("error") == expected.get("error")
            detail = (
                ""
                if ok
                else f"error: expected {expected.get('error')!r}, got {output.get('error')!r}"
            )
            return ScoreResult(passed=ok, score=1.0 if ok else 0.0, detail=detail)

        # kind == "shape"
        layer_ok = output.get("layer") == expected.get("layer")
        want_keys = set(expected.get("keys", []))
        got_keys = set(output.get("keys", []))
        keys_ok = want_keys.issubset(got_keys)
        ok = layer_ok and keys_ok
        if ok:
            return ScoreResult(passed=True, score=1.0)
        problems = []
        if not layer_ok:
            problems.append(
                f"layer: expected {expected.get('layer')!r}, got {output.get('layer')!r}"
            )
        if not keys_ok:
            problems.append(f"missing keys: {sorted(want_keys - got_keys)}")
        return ScoreResult(passed=False, score=0.0, detail="; ".join(problems))
