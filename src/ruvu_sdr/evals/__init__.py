"""Plane 07 — the eval substrate (playbook Part 6).

Four parts: case store, runner, scorers, registry. The same harness runs
fast-and-narrow on every PR and slow-and-broad nightly. It holds zero cases in
Phase 0; the six dimensions populate as the build phases reach them.
"""

from ruvu_sdr.evals.models import Case, CaseResult, Dimension, EvalResult, ScoreResult
from ruvu_sdr.evals.scorers import ExactMatchScorer, Scorer

# NOTE: EvalRunner is intentionally *not* re-exported here. It lives in
# ruvu_sdr.evals.runner, which is also the `python -m ruvu_sdr.evals.runner`
# entrypoint; importing it in this package __init__ triggers a runpy
# double-import RuntimeWarning. Import it from ruvu_sdr.evals.runner directly.

__all__ = [
    "Case",
    "CaseResult",
    "Dimension",
    "EvalResult",
    "ScoreResult",
    "Scorer",
    "ExactMatchScorer",
]
