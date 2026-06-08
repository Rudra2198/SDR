"""Contract-eval target + fake client for the hubspot-mcp tools (Parts 6, 8).

Mirrors ``context_api/contract.py``: run a tool with an injected fake client and
normalize the result into a small, scorable shape. No token, no network — the fake
is driven by a named ``scenario`` so the golden set can exercise success, a 404,
and an error path deterministically.

``FakeHubSpotClient`` is a small stateful in-memory HubSpot for notes (associations
read + batch read + create), so it backs both this eval and the idempotency-replay
unit test. It is the permanent test double; the real ``HubSpotClient`` is the
production path.

A case input is ``{"tool": <name>, "scenario": <fake setup>, "args": {...}}``.
The normalized output is one of:
  ``{"kind": "shape", "keys": [...]}``                  a model was returned
  ``{"kind": "none"}``                                  the tool returned None (e.g. 404)
  ``{"kind": "raises", "error": "HubSpotError"}``       the tool surfaced a HubSpotError
  ``{"kind": "unimplemented"}``                         the tool is still a stub (eval-first)
"""

from __future__ import annotations

from typing import Any

from ruvu_sdr.mcp_servers.hubspot import tools
from ruvu_sdr.mcp_servers.hubspot.client import HubSpotError

# ─── Canned HubSpot payloads (raw API shape; tools normalize these) ───────────
_CONTACTS_PAGE: dict[str, Any] = {
    "results": [
        {
            "id": "101",
            "properties": {
                "email": "ash@acme.com",
                "firstname": "Ash",
                "lastname": "Patel",
                "jobtitle": "Founder",
                "company": "Acme",
            },
        },
        {
            "id": "102",
            "properties": {
                "email": "bo@globex.com",
                "firstname": "Bo",
                "lastname": "Lee",
                "jobtitle": "VP Engineering",
                "company": "Globex",
            },
        },
    ],
    "paging": {"next": {"after": "103"}},
}
_COMPANY: dict[str, Any] = {
    "id": "789",
    "properties": {"name": "Acme", "domain": "acme.com", "industry": "SaaS"},
}


class FakeHubSpotClient:
    """In-memory stand-in for ``HubSpotClientProtocol``, driven by a scenario.

    Scenarios: ``ok`` (canned success), ``not_found`` (company GET -> 404),
    ``auth_error`` (any GET -> 401). Notes created via ``post`` persist in-memory
    and become visible to the associations/batch-read reads, so a second
    ``log_activity`` with the same idempotency key finds the marker and no-ops.
    """

    def __init__(self, scenario: str = "ok") -> None:
        self.scenario = scenario
        self._notes: dict[str, dict[str, Any]] = {}  # note_id -> note object
        self._assoc: dict[str, list[str]] = {}  # contact_id -> [note_id, ...]
        self._seq = 0

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.scenario == "auth_error":
            raise HubSpotError(401, "invalid token")
        if path.startswith("/crm/v3/objects/contacts") and "/associations/notes" in path:
            contact_id = path.split("/contacts/")[1].split("/")[0]
            return {"results": [{"toObjectId": nid} for nid in self._assoc.get(contact_id, [])]}
        if path.startswith("/crm/v3/objects/contacts"):
            return _CONTACTS_PAGE
        if path.startswith("/crm/v3/objects/companies/"):
            if self.scenario == "not_found":
                raise HubSpotError(404, "company not found")
            return _COMPANY
        return {}

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.scenario == "auth_error":
            raise HubSpotError(401, "invalid token")
        json = json or {}
        if path == "/crm/v3/objects/notes/batch/read":
            wanted = {item["id"] for item in json.get("inputs", [])}
            return {"results": [n for nid, n in self._notes.items() if nid in wanted]}
        if path == "/crm/v3/objects/notes":
            self._seq += 1
            note_id = str(900 + self._seq)
            self._notes[note_id] = {"id": note_id, "properties": dict(json.get("properties", {}))}
            for assoc in json.get("associations", []):
                contact_id = str(assoc["to"]["id"])
                self._assoc.setdefault(contact_id, []).append(note_id)
            return {"id": note_id}
        return {}


def hubspot_contract_target(case_input: dict[str, Any]) -> dict[str, Any]:
    """Run one hubspot tool against the fake client and normalize for scoring."""
    tool_name = case_input["tool"]
    scenario = case_input.get("scenario", "ok")
    args = case_input.get("args", {})
    client = FakeHubSpotClient(scenario)
    fn = getattr(tools, tool_name)
    try:
        result = fn(client, **args)
    except NotImplementedError:
        return {"kind": "unimplemented"}
    except HubSpotError:
        return {"kind": "raises", "error": "HubSpotError"}

    if result is None:
        return {"kind": "none"}
    return {"kind": "shape", "keys": sorted(result.model_dump().keys())}
