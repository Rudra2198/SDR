"""Case store (playbook Part 6): eval cases live in files and/or Postgres, versioned.

Three implementations behind one interface:
- `FileCaseStore`   — golden sets as JSON on disk (the default; versioned in git).
- `PostgresCaseStore`— the `eval_cases` table (for cases curated/labeled in the DB).
- `InMemoryCaseStore`— for tests and prototyping.

Phase 0 ships zero cases; the golden sets fill in as phases reach them.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from ruvu_sdr.evals.models import Case, Dimension

# Repo-root golden sets dir: src/ruvu_sdr/evals/case_store.py -> parents[3] == repo root.
DEFAULT_CASES_DIR = Path(__file__).resolve().parents[3] / "golden_sets"


class CaseStore(ABC):
    """Loads the cases for a named eval."""

    @abstractmethod
    def load(self, eval_name: str) -> list[Case]:
        """Return all cases registered for ``eval_name`` (possibly empty)."""


class FileCaseStore(CaseStore):
    """Loads cases from ``<root>/<eval_name>.json``.

    Each file is a JSON list of objects with at least ``input`` and ``expected``,
    optionally ``id``, ``dimension``, and ``metadata``.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_CASES_DIR

    def load(self, eval_name: str) -> list[Case]:
        path = self.root / f"{eval_name}.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text())
        return [
            Case(
                eval_name=eval_name,
                input=item["input"],
                expected=item["expected"],
                id=item.get("id"),
                dimension=Dimension(item["dimension"]) if item.get("dimension") else None,
                metadata=item.get("metadata", {}),
            )
            for item in raw
        ]


class PostgresCaseStore(CaseStore):
    """Loads cases from the ``eval_cases`` table (Part 10)."""

    def load(self, eval_name: str) -> list[Case]:
        from ruvu_sdr.db import get_cursor

        with get_cursor() as cur:
            cur.execute(
                "SELECT id, dimension, input, expected FROM eval_cases "
                "WHERE eval_name = %s ORDER BY created_at;",
                (eval_name,),
            )
            rows = cur.fetchall()
        return [
            Case(
                eval_name=eval_name,
                id=str(row["id"]),
                dimension=Dimension(row["dimension"]) if row["dimension"] else None,
                input=row["input"],
                expected=row["expected"],
            )
            for row in rows
        ]


class InMemoryCaseStore(CaseStore):
    """In-memory store keyed by eval name. For tests and prototyping."""

    def __init__(self, cases_by_eval: dict[str, list[Case]]) -> None:
        self._cases = cases_by_eval

    def load(self, eval_name: str) -> list[Case]:
        return list(self._cases.get(eval_name, []))
