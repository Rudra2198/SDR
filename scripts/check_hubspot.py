"""Phase 1 smoke test: confirm hubspot-mcp talks to live HubSpot (and traces land).

Read-only by default: pulls a few contacts and one company through the real tools,
which also emits Langfuse traces (the tools are @observe-wrapped and this process
calls configure_tracing()). Pass --write CONTACT_ID to also exercise the write path
(log_activity) twice and prove idempotency against the live CRM — it creates at most
one note thanks to the in-body marker, even across repeated runs.

    uv run python scripts/check_hubspot.py                 # read-only
    uv run python scripts/check_hubspot.py --write 12345   # also test log_activity
"""

from __future__ import annotations

import argparse
import sys

from ruvu_sdr.mcp_servers.hubspot import tools
from ruvu_sdr.mcp_servers.hubspot.client import HubSpotClient
from ruvu_sdr.observability import configure_tracing, current_trace_url, flush, observe

# Fixed so re-running the smoke is itself idempotent (no note pile-up).
_SMOKE_IDEM_KEY = "ruvu-sdr-smoke-test"


@observe(name="hubspot-smoke")
def _smoke(client: HubSpotClient, write_contact_id: str | None) -> dict:
    out: dict[str, object] = {}

    page = tools.read_contacts(client, limit=3)
    out["contacts_read"] = len(page.contacts)
    out["sample_contact"] = page.contacts[0].model_dump() if page.contacts else None
    out["has_next_page"] = page.next_after is not None

    companies = client.get("/crm/v3/objects/companies", params={"limit": 1}).get("results", [])
    if companies:
        company = tools.read_company(client, companies[0]["id"])
        out["sample_company"] = company.model_dump() if company else None

    if write_contact_id:
        first = tools.log_activity(
            client, write_contact_id, "Ruvu SDR smoke test note.", _SMOKE_IDEM_KEY
        )
        second = tools.log_activity(
            client, write_contact_id, "Ruvu SDR smoke test note.", _SMOKE_IDEM_KEY
        )
        out["write"] = {
            "engagement_id": first.engagement_id,
            "first_created": first.created,
            "second_idempotent_hit": second.idempotent_hit,
            "no_double_log": first.engagement_id == second.engagement_id,
        }

    out["trace_url"] = current_trace_url()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test hubspot-mcp against live HubSpot.")
    parser.add_argument(
        "--write",
        metavar="CONTACT_ID",
        help="also exercise log_activity (writes a note) against this contact id",
    )
    args = parser.parse_args(argv)

    traced = configure_tracing()
    print(f"tracing: {'on' if traced else 'off (no Langfuse keys in .env)'}")

    try:
        client = HubSpotClient()
    except ValueError as err:
        print(f"HubSpot not configured: {err}")
        return 1

    with client:
        result = _smoke(client, args.write)
    flush()  # short-lived process: flush before exit or the trace is lost

    for key, value in result.items():
        print(f"  {key}: {value}")
    print("\nHubSpot reads succeeded.")
    if not result.get("trace_url") and traced:
        print("Trace sent; open Langfuse -> Traces -> 'hubspot-smoke' to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
