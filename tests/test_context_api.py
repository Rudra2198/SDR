"""Phase 1 unit tests for the Context API (Plane 05, playbook Part 3).

Two layers of checks:
- Pure (no DB): the three stubbed layers raise `NotImplementedForTenant`, and the
  contract scorer scores shape/raises cases correctly.
- DB-backed: the three live layers return the `ContextResult` envelope with the
  right layer and payload. These skip cleanly when Postgres is not reachable, so a
  fresh checkout without Docker still passes; CI (Postgres up, migrations applied)
  exercises them for real.

These same assertions also run through the harness as the `context_api_contract`
unit eval (the slice's gate).
"""

from __future__ import annotations

import pytest

from ruvu_sdr.context_api import ContextAPI, ContextResult, Layer, NotImplementedForTenant
from ruvu_sdr.context_api.contract import context_contract_target
from ruvu_sdr.db import get_cursor
from ruvu_sdr.evals import ContextContractScorer
from ruvu_sdr.evals.case_store import FileCaseStore
from ruvu_sdr.evals.registry import REGISTRY
from ruvu_sdr.evals.runner import EvalRunner


def _db_up() -> bool:
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1;")
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable")


# ─── Stubbed layers (no DB) ───────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("method", "args", "layer"),
    [
        ("graph_path", {"a": "Ash", "b": "Acme"}, Layer.GRAPH),
        ("search", {"query": "warm intros", "k": 5}, Layer.VECTOR),
        ("doc", {"uri": "s3://x"}, Layer.DOCUMENT),
    ],
)
def test_stubbed_layers_raise(method: str, args: dict, layer: Layer) -> None:
    ctx = ContextAPI()
    with pytest.raises(NotImplementedForTenant) as exc:
        getattr(ctx, method)(**args)
    assert exc.value.tenant_id == "ruvu"
    assert exc.value.layer == str(layer)
    assert exc.value.method == method


def test_tenant_id_defaults_and_overrides() -> None:
    assert ContextAPI().tenant_id == "ruvu"
    assert ContextAPI(tenant_id="acme").tenant_id == "acme"


# ─── Contract scorer (no DB) ──────────────────────────────────────────────────
def test_contract_scorer_shape_pass_and_fail() -> None:
    scorer = ContextContractScorer()
    expected = {"kind": "shape", "layer": "semantic", "keys": ["data", "layer"]}
    ok = {"kind": "shape", "layer": "semantic", "keys": ["data", "layer", "source"]}
    assert scorer.score(expected=expected, output=ok).passed is True
    wrong_layer = {"kind": "shape", "layer": "episodic", "keys": ["data", "layer"]}
    assert scorer.score(expected=expected, output=wrong_layer).passed is False
    missing_key = {"kind": "shape", "layer": "semantic", "keys": ["data"]}
    assert scorer.score(expected=expected, output=missing_key).passed is False


def test_contract_scorer_raises_and_kind_mismatch() -> None:
    scorer = ContextContractScorer()
    expected = {"kind": "raises", "error": "NotImplementedForTenant"}
    assert scorer.score(expected=expected, output=expected).passed is True
    wrong_err = {"kind": "raises", "error": "ValueError"}
    assert scorer.score(expected=expected, output=wrong_err).passed is False
    # A stub that wrongly returned a shape must fail (kind mismatch).
    shape = {"kind": "shape", "layer": "semantic", "keys": []}
    assert scorer.score(expected=expected, output=shape).passed is False


def test_target_normalizes_stub_to_raises() -> None:
    out = context_contract_target({"method": "doc", "args": {"uri": "s3://x"}})
    assert out == {"kind": "raises", "error": "NotImplementedForTenant"}


# ─── Live layers (DB-backed) ──────────────────────────────────────────────────
@requires_db
def test_metric_contact_funnel_shape() -> None:
    res = ContextAPI().metric("contact_funnel")
    assert isinstance(res, ContextResult)
    assert res.layer is Layer.SEMANTIC
    assert res.tenant_id == "ruvu"
    assert res.source == "postgres:semantic_contact_funnel"
    assert isinstance(res.data, dict)  # {state: count}, possibly empty


@requires_db
def test_metric_reply_rate_shape() -> None:
    res = ContextAPI().metric("reply_rate")
    assert res.layer is Layer.SEMANTIC
    assert set(res.data) == {"value", "replied", "sent"}
    assert res.data["value"] == 0.0  # no send path yet (Phase 3)


@requires_db
def test_metric_unknown_name_raises() -> None:
    with pytest.raises(ValueError, match="unknown metric"):
        ContextAPI().metric("does_not_exist")


@requires_db
def test_recall_shape() -> None:
    res = ContextAPI().recall("first_touch")
    assert res.layer is Layer.EPISODIC
    assert res.source == "postgres:episodic_memory"
    assert isinstance(res.data, list)


@requires_db
def test_user_prefs_returns_brand_rules() -> None:
    res = ContextAPI().user_prefs()
    assert res.layer is Layer.USER
    assert res.source == "postgres:tenant_prefs"
    assert "voice" in res.data
    assert any("em-dash" in rule for rule in res.data["rules"])


@requires_db
def test_user_prefs_unknown_tenant_raises() -> None:
    with pytest.raises(KeyError):
        ContextAPI(tenant_id="no-such-tenant").user_prefs()


@requires_db
def test_contract_eval_passes_via_harness() -> None:
    # The slice's actual gate: the registered eval over its golden set is green.
    spec = REGISTRY["context_api_contract"]
    result = EvalRunner(case_store=FileCaseStore()).run_eval(spec)
    assert result.passed is True
    assert result.num_cases == 7
