"""Eval runner (playbook Part 6): executes a suite's cases against current code.

For each eval in the suite it loads cases from the case store, runs the target on
each input, scores the output, and aggregates a verdict. With no cases an eval
passes vacuously, so the PR gate is green until real evals are registered, then
it grows teeth phase by phase.

CLI (this is what CI calls):

    uv run python -m ruvu_sdr.evals.runner --suite pr
"""

from __future__ import annotations

import argparse
import sys

from ruvu_sdr.evals.case_store import CaseStore, FileCaseStore
from ruvu_sdr.evals.models import CaseResult, EvalResult
from ruvu_sdr.evals.registry import AVAILABLE_SUITES, EvalSpec, suite_specs


class EvalRunner:
    """Runs eval specs against a case store. Pure: no I/O beyond the store/target."""

    def __init__(self, case_store: CaseStore | None = None) -> None:
        self.case_store = case_store or FileCaseStore()

    def run_eval(self, spec: EvalSpec) -> EvalResult:
        cases = self.case_store.load(spec.name)
        case_results: list[CaseResult] = []
        for case in cases:
            output = spec.target(case.input)
            score = spec.scorer.score(expected=case.expected, output=output)
            case_results.append(CaseResult(case=case, output=output, score=score))

        if case_results:
            mean = sum(cr.score.score for cr in case_results) / len(case_results)
            passed = all(cr.score.passed for cr in case_results)
        else:
            mean, passed = 1.0, True  # vacuous pass — no cases registered yet

        return EvalResult(
            eval_name=spec.name,
            dimension=spec.dimension,
            passed=passed,
            score=mean,
            case_results=case_results,
        )

    def run_suite(self, suite: str) -> list[EvalResult]:
        return [self.run_eval(spec) for spec in suite_specs(suite)]


def _summarize(suite: str, results: list[EvalResult]) -> bool:
    total_cases = sum(r.num_cases for r in results)
    passed = all(r.passed for r in results)
    verdict = "PASS" if passed else "FAIL"
    print(f"[eval:{suite}] {len(results)} eval(s), {total_cases} case(s) -> {verdict}")
    for r in results:
        rv = "PASS" if r.passed else "FAIL"
        print(
            f"  - {r.eval_name} [{r.dimension.value}]: {rv} "
            f"(score={r.score:.2f}, {r.num_cases} cases)"
        )
    if not results:
        print("  (no evals registered for this suite yet — gate passes vacuously)")
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Ruvu SDR eval suite.")
    parser.add_argument(
        "--suite",
        default="pr",
        choices=AVAILABLE_SUITES,
        help="which eval schedule to run (default: pr)",
    )
    args = parser.parse_args(argv)

    results = EvalRunner().run_suite(args.suite)
    passed = _summarize(args.suite, results)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
