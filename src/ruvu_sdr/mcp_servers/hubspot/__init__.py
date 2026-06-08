"""hubspot-mcp (Plane 04) — read contacts/companies, log activity back.

Three layers, no monolith (playbook Part 8):
- ``client``  — the only thing that touches the HubSpot network (httpx).
- ``tools``   — pure, traced functions returning shapes normalized to the Part 10
  schema; the orchestrator calls these directly, the MCP server wraps them.
- ``server``  — the standalone FastMCP server exposing the tools.

Tools depend on the ``HubSpotClientProtocol`` interface, so tests and the contract
eval inject a fake and run with no token and no network.
"""
