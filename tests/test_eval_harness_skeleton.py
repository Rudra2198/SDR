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


def test_runner_passes_vacuously_with_no_cases() -> None:
    # Customer 01 behavior: an eval with zero cases still executes and passes
    # green. (Phase 0 proved this on the empty PR suite; Phase 1 registered the
    # first real eval, so we show the invariant directly via an empty store.)
    spec = EvalSpec(
        name="selftest_empty",
        dimension=Dimension.UNIT,
        gates_phase="phase-0",
        scorer=ExactMatchScorer(),
        target=str.upper,
    )
    result = EvalRunner(case_store=InMemoryCaseStore({})).run_eval(spec)
    assert result.num_cases == 0
    assert result.passed is True  # vacuous pass
    assert result.score == 1.0


def test_pr_suite_carries_phase_1_eval() -> None:
    # The gate now has teeth: the Context API contract eval runs on every PR.
    names = [spec.name for spec in suite_specs("pr")]
    assert "context_api_contract" in names


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
