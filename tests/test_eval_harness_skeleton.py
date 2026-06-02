"""Phase 0 unit check: the eval harness skeleton itself works.

This is a `unit`-dimension test (Part 6): the PR gate passes vacuously with zero
registered evals, and the runner/scorer/registry machinery produces correct
verdicts when given real cases.
"""

from __future__ import annotations

from ruvu_sdr.evals import Case, Dimension, ExactMatchScorer
from ruvu_sdr.evals.case_store import InMemoryCaseStore
from ruvu_sdr.evals.registry import EvalSpec, suite_specs
from ruvu_sdr.evals.runner import EvalRunner


def test_pr_suite_empty_and_passes() -> None:
    # Customer 01 behavior: with nothing registered for PRs, the gate is green
    # but the harness still executes.
    assert suite_specs("pr") == []
    results = EvalRunner().run_suite("pr")
    assert results == []
    assert all(r.passed for r in results)  # vacuously true


def test_exact_match_scorer() -> None:
    scorer = ExactMatchScorer()
    assert scorer.score(expected="x", output="x").passed is True
    assert scorer.score(expected="x", output="y").passed is False


def test_runner_executes_and_scores_passing_cases() -> None:
    # Full loop: case store -> target -> scorer -> aggregate.
    name = "selftest_upper"
    store = InMemoryCaseStore(
        {
            name: [
                Case(eval_name=name, input="hello", expected="HELLO"),
                Case(eval_name=name, input="ab", expected="AB"),
            ]
        }
    )
    spec = EvalSpec(
        name=name,
        dimension=Dimension.UNIT,
        gates_phase="phase-0",
        scorer=ExactMatchScorer(),
        target=str.upper,
        description="self-test",
    )
    result = EvalRunner(case_store=store).run_eval(spec)
    assert result.passed is True
    assert result.num_cases == 2
    assert result.score == 1.0


def test_runner_flags_failures() -> None:
    name = "selftest_fail"
    store = InMemoryCaseStore({name: [Case(eval_name=name, input="hello", expected="WRONG")]})
    spec = EvalSpec(
        name=name,
        dimension=Dimension.UNIT,
        gates_phase="phase-0",
        scorer=ExactMatchScorer(),
        target=str.upper,
    )
    result = EvalRunner(case_store=store).run_eval(spec)
    assert result.passed is False
    assert result.score == 0.0
