"""hubspot-mcp FastMCP server (Plane 04) — the standalone, reusable tool surface.

Exposes the three pure tools (``read_contacts``, ``read_company``, ``log_activity``)
as MCP tools. The MCP layer is thin: it owns the real ``HubSpotClient`` (one per
process) and delegates all logic to the pure functions, so the orchestrator can
call those same functions directly without going through MCP (playbook Part 8;
business logic stays in pure functions, Part 12).

Run standalone:

    uv run python -m ruvu_sdr.mcp_servers.hubspot.server
"""

from __future__ import annotations

from functools import lru_cache

from fastmcp import FastMCP

from ruvu_sdr.mcp_servers.hubspot import tools
from ruvu_sdr.mcp_servers.hubspot.client import HubSpotClient
from ruvu_sdr.mcp_servers.hubspot.tools import ActivityResult, Company, ContactsPage
from ruvu_sdr.observability import configure_tracing

mcp = FastMCP("hubspot")


@lru_cache(maxsize=1)
def _client() -> HubSpotClient:
    """The process-wide real HubSpot client (lazy so import needs no token)."""
    return HubSpotClient()


@mcp.tool
def read_contacts(limit: int = 10, after: str | None = None) -> ContactsPage:
    """Read a page of contacts from HubSpot, normalized to the SDR schema.

    ``after`` is the paging cursor from a previous call (null to start).
    """
    return tools.read_contacts(_client(), limit=limit, after=after)


@mcp.tool
def read_company(company_id: str) -> Company | None:
    """Read one company by its HubSpot id, or null if it does not exist."""
    return tools.read_company(_client(), company_id)


@mcp.tool
def log_activity(contact_id: str, body: str, idempotency_key: str) -> ActivityResult:
    """Log a note to a contact. Idempotent on ``idempotency_key`` (no double-logs)."""
    return tools.log_activity(_client(), contact_id, body, idempotency_key)


def main() -> None:
    """Entry point: configure tracing, then serve over stdio."""
    configure_tracing()
    mcp.run()


if __name__ == "__main__":
    main()
