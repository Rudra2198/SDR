"""Phase 1 unit tests for hubspot-mcp (Plane 04, playbook Part 8).

All hermetic — no token, no network. Two kinds of double:
- ``FakeHubSpotClient`` (a stateful in-memory HubSpot) exercises the tools and the
  idempotency replay.
- ``httpx.MockTransport`` exercises the real ``HubSpotClient``'s parsing and the
  non-2xx -> ``HubSpotError`` mapping.

The same contract these assert also runs through the harness as the
``hubspot_tool_contract`` unit eval (the slice's gate), asserted at the bottom.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from ruvu_sdr.evals.registry import REGISTRY
from ruvu_sdr.evals.runner import EvalRunner
from ruvu_sdr.mcp_servers.hubspot import server, tools
from ruvu_sdr.mcp_servers.hubspot.client import (
    HubSpotClient,
    HubSpotClientProtocol,
    HubSpotError,
)
from ruvu_sdr.mcp_servers.hubspot.contract import FakeHubSpotClient


def _client_over(handler) -> HubSpotClient:
    """A real HubSpotClient whose transport is a MockTransport (no network)."""
    return HubSpotClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.hubapi.com"
        )
    )


# ─── tools: read_contacts ─────────────────────────────────────────────────────


def test_read_contacts_normalizes_to_schema():
    page = tools.read_contacts(FakeHubSpotClient("ok"), limit=2)
    assert page.next_after == "103"
    assert [c.hubspot_id for c in page.contacts] == ["101", "102"]
    first = page.contacts[0]
    assert first.email == "ash@acme.com"
    assert first.first_name == "Ash"
    assert first.last_name == "Patel"
    assert first.title == "Founder"
    assert first.company == "Acme"


def test_read_contacts_passes_after_cursor():
    seen: dict[str, object] = {}

    class CursorClient:
        def get(self, path, params=None):
            seen.update(params or {})
            return {"results": [], "paging": {}}

        def post(self, path, json=None):
            return {}

    page = tools.read_contacts(CursorClient(), limit=5, after="103")
    assert seen["after"] == "103"
    assert seen["limit"] == 5
    assert page.contacts == []
    assert page.next_after is None  # no paging.next -> end of list


# ─── tools: read_company ──────────────────────────────────────────────────────


def test_read_company_normalizes():
    company = tools.read_company(FakeHubSpotClient("ok"), "789")
    assert company is not None
    assert company.hubspot_id == "789"
    assert company.name == "Acme"
    assert company.domain == "acme.com"
    assert company.industry == "SaaS"


def test_read_company_404_returns_none():
    assert tools.read_company(FakeHubSpotClient("not_found"), "000") is None


def test_read_company_non_404_propagates():
    client = _client_over(lambda req: httpx.Response(500, text="boom"))
    with pytest.raises(HubSpotError) as exc:
        tools.read_company(client, "789")
    assert exc.value.status == 500


# ─── tools: log_activity idempotency ──────────────────────────────────────────


def test_log_activity_creates_then_replays_idempotently():
    client = FakeHubSpotClient("ok")
    first = tools.log_activity(client, "101", "First touch sent.", "c101-t1")
    second = tools.log_activity(client, "101", "First touch sent.", "c101-t1")

    assert first.created is True and first.idempotent_hit is False
    assert second.created is False and second.idempotent_hit is True
    assert first.engagement_id == second.engagement_id  # no double-log


def test_log_activity_distinct_keys_create_distinct_notes():
    client = FakeHubSpotClient("ok")
    a = tools.log_activity(client, "101", "touch 1", "c101-t1")
    b = tools.log_activity(client, "101", "touch 2", "c101-t2")
    assert a.engagement_id != b.engagement_id
    assert a.created and b.created


def test_log_activity_embeds_idem_marker_in_body():
    client = FakeHubSpotClient("ok")
    tools.log_activity(client, "101", "hello", "c101-t1")
    # the created note body carries the hidden marker we scan for on replay
    body = next(iter(client._notes.values()))["properties"]["hs_note_body"]
    assert "<!--ruvu-idem:c101-t1-->" in body


# ─── real client: HubSpotClient parsing + error mapping (MockTransport) ────────


def test_client_returns_json_on_2xx():
    client = _client_over(lambda req: httpx.Response(200, json={"hello": "world"}))
    assert client.get("/anything") == {"hello": "world"}


def test_client_empty_body_returns_empty_dict():
    client = _client_over(lambda req: httpx.Response(204))
    assert client.get("/anything") == {}


@pytest.mark.parametrize("status", [400, 401, 404, 429, 500])
def test_client_non_2xx_raises_hubspot_error(status):
    client = _client_over(lambda req: httpx.Response(status, text="nope"))
    with pytest.raises(HubSpotError) as exc:
        client.get("/anything")
    assert exc.value.status == status


def test_client_satisfies_protocol():
    client = _client_over(lambda req: httpx.Response(200, json={}))
    assert isinstance(client, HubSpotClientProtocol)


def test_client_requires_a_token(monkeypatch):
    monkeypatch.setattr(
        "ruvu_sdr.mcp_servers.hubspot.client.get_settings",
        lambda: type("S", (), {"hubspot_access_token": None})(),
    )
    with pytest.raises(ValueError, match="HUBSPOT_ACCESS_TOKEN"):
        HubSpotClient()


# ─── MCP server: registration + call path ─────────────────────────────────────


def test_server_registers_three_tools_without_exposing_client():
    tool_list = asyncio.run(server.mcp.list_tools())
    by_name = {t.name: t for t in tool_list}
    assert set(by_name) == {"read_contacts", "read_company", "log_activity"}
    # the injected client dependency must not leak into the MCP-facing schema
    for t in tool_list:
        assert "client" not in t.parameters.get("properties", {})


def test_server_call_path_uses_pure_tools(monkeypatch):
    fake = FakeHubSpotClient("ok")
    monkeypatch.setattr(server, "_client", lambda: fake)
    result = asyncio.run(server.mcp.call_tool("read_contacts", {"limit": 2}))
    assert result.structured_content["next_after"] == "103"
    assert len(result.structured_content["contacts"]) == 2


# ─── the slice gate: the contract eval passes ─────────────────────────────────


def test_hubspot_tool_contract_eval_passes():
    result = EvalRunner().run_eval(REGISTRY["hubspot_tool_contract"])
    assert result.passed
    assert result.num_cases == 5
