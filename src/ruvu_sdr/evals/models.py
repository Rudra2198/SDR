"""Core data types for the eval substrate (Plane 07, playbook Part 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Dimension(StrEnum):
    """The six eval dimensions (Part 6). They come online phase by phase."""

    UNIT = "unit"  # tool calls, schemas, deterministic — Week 1
    COMPONENT = "component"  # single agent step, LLM-as-judge — Weeks 2-3
    SYSTEM = "system"  # end-to-end task, human-graded sample — Week 4
    ADVERSARIAL = "adversarial"  # prompt injection / jailbreak — Weeks 4-5
    FAIRNESS = "fairness"  # slice-level parity — Week 5
    OPERATIONAL = "operational"  # cost / latency / drift — Week 6


@dataclass(frozen=True)
class Case:
    """A single eval case: an input and its expected result, for a named eval."""

    eval_name: str
    input: Any
    expected: Any
    id: str | None = None
    dimension: Dimension | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreResult:
    """The verdict for scoring one case. `score` is normalized 0.0-1.0."""

    passed: bool
    score: float
    detail: str = ""


@dataclass(frozen=True)
class CaseResult:
    """A case, the output the target produced for it, and its score."""

    case: Case
    output: Any
    score: ScoreResult


@dataclass(frozen=True)
class EvalResult:
    """Aggregate result for one eval over all its cases."""

    eval_name: str
    dimension: Dimension
    passed: bool
    score: float  # mean of case scores (1.0 when there are no cases yet)
    case_results: list[CaseResult] = field(default_factory=list)
    detail: str = ""

    @property
    def num_cases(self) -> int:
        return len(self.case_results)
