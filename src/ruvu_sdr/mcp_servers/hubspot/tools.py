"""hubspot-mcp tools (Plane 04) — pure, traced functions over a HubSpot client.

Three tools, each taking an injected ``HubSpotClientProtocol`` so tests/evals use a
fake (no token, no network). Returns are normalized to the Part 10 schema via
pydantic models, never raw HubSpot JSON, so the orchestrator stays decoupled from
HubSpot's property names. Every tool is ``@observe``-traced (Part 4, rule 6).

``log_activity`` is idempotent (rule 5): it embeds a hidden marker derived from
``idempotency_key`` in the note body and checks the contact's existing notes before
posting, so a retry never double-logs. (The Postgres ``touches.idempotency_key``
guard is the second layer, added with the orchestrator.)
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from ruvu_sdr.mcp_servers.hubspot.client import HubSpotClientProtocol, HubSpotError
from ruvu_sdr.observability import observe, tag_observation

# Properties we read (HubSpot returns its own defaults too; we map only these).
_CONTACT_PROPERTIES = "email,firstname,lastname,jobtitle,company"
_COMPANY_PROPERTIES = "name,domain,industry"
# HubSpot-defined association type for a Note -> Contact.
_NOTE_TO_CONTACT_TYPE_ID = 202

# ─── Normalized return shapes (Part 10 schema, not raw HubSpot JSON) ──────────


class Contact(BaseModel):
    """A contact, mapped to the ``contacts`` table columns."""

    hubspot_id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    company: str | None = None


class ContactsPage(BaseModel):
    """One page of contacts plus the cursor for the next page (``None`` at end)."""

    contacts: list[Contact]
    next_after: str | None = None


class Company(BaseModel):
    """A company, for enrichment context."""

    hubspot_id: str
    name: str | None = None
    domain: str | None = None
    industry: str | None = None


class ActivityResult(BaseModel):
    """Outcome of ``log_activity``. ``created`` is False on an idempotent replay."""

    engagement_id: str
    created: bool
    idempotent_hit: bool


# ─── Normalizers (raw HubSpot object -> model) ────────────────────────────────


def _to_contact(obj: dict) -> Contact:
    p = obj.get("properties", {})
    return Contact(
        hubspot_id=str(obj["id"]),
        email=p.get("email"),
        first_name=p.get("firstname"),
        last_name=p.get("lastname"),
        title=p.get("jobtitle"),
        company=p.get("company"),
    )


def _to_company(obj: dict) -> Company:
    p = obj.get("properties", {})
    return Company(
        hubspot_id=str(obj["id"]),
        name=p.get("name"),
        domain=p.get("domain"),
        industry=p.get("industry"),
    )


# ─── Tools ────────────────────────────────────────────────────────────────────


@observe(name="hubspot.read_contacts")
def read_contacts(
    client: HubSpotClientProtocol, limit: int = 10, after: str | None = None
) -> ContactsPage:
    """Read a page of contacts, normalized to ``Contact``. ``after`` is the cursor."""
    tag_observation(tool="read_contacts", limit=limit, after=after)
    params: dict[str, object] = {"limit": limit, "properties": _CONTACT_PROPERTIES}
    if after is not None:
        params["after"] = after
    data = client.get("/crm/v3/objects/contacts", params=params)
    contacts = [_to_contact(obj) for obj in data.get("results", [])]
    next_after = data.get("paging", {}).get("next", {}).get("after")
    return ContactsPage(contacts=contacts, next_after=next_after)


@observe(name="hubspot.read_company")
def read_company(client: HubSpotClientProtocol, company_id: str) -> Company | None:
    """Read one company by id, or ``None`` if HubSpot returns 404."""
    tag_observation(tool="read_company", company_id=company_id)
    try:
        data = client.get(
            f"/crm/v3/objects/companies/{company_id}",
            params={"properties": _COMPANY_PROPERTIES},
        )
    except HubSpotError as err:
        if err.status == 404:
            return None
        raise
    return _to_company(data)


@observe(name="hubspot.log_activity")
def log_activity(
    client: HubSpotClientProtocol, contact_id: str, body: str, idempotency_key: str
) -> ActivityResult:
    """Log a note to a contact, idempotent on ``idempotency_key`` (check before act)."""
    tag_observation(tool="log_activity", contact_id=contact_id, idempotency_key=idempotency_key)
    marker = _idem_marker(idempotency_key)

    existing_id = _find_note_by_marker(client, contact_id, marker)
    if existing_id is not None:
        tag_observation(idempotent_hit=True)
        return ActivityResult(engagement_id=existing_id, created=False, idempotent_hit=True)

    created = client.post(
        "/crm/v3/objects/notes",
        json={
            "properties": {
                "hs_note_body": f"{body}\n{marker}",
                "hs_timestamp": datetime.now(UTC).isoformat(),
            },
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": _NOTE_TO_CONTACT_TYPE_ID,
                        }
                    ],
                }
            ],
        },
    )
    return ActivityResult(engagement_id=str(created["id"]), created=True, idempotent_hit=False)


def _idem_marker(idempotency_key: str) -> str:
    """A hidden, body-embedded marker we scan for to detect a prior identical log."""
    return f"<!--ruvu-idem:{idempotency_key}-->"


def _find_note_by_marker(client: HubSpotClientProtocol, contact_id: str, marker: str) -> str | None:
    """Return the id of an existing note on this contact carrying ``marker``, else None."""
    assoc = client.get(f"/crm/v3/objects/contacts/{contact_id}/associations/notes")
    note_ids = [str(r.get("toObjectId") or r.get("id")) for r in assoc.get("results", [])]
    if not note_ids:
        return None
    read = client.post(
        "/crm/v3/objects/notes/batch/read",
        json={"properties": ["hs_note_body"], "inputs": [{"id": nid} for nid in note_ids]},
    )
    for note in read.get("results", []):
        if marker in (note.get("properties", {}).get("hs_note_body") or ""):
            return str(note["id"])
    return None
