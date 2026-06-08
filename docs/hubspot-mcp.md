# hubspot-mcp (Plane 04, Tooling / MCP)

One of the four standalone FastMCP servers. It reads contacts and companies from
HubSpot and logs activity (notes) back. Every external system is its own MCP server,
reusable across clients; MCP servers never call each other and hold no state (playbook
Parts 4 and 8). Spec: [`ruvu-sdr-agent-playbook.md`](../ruvu-sdr-agent-playbook.md) Part 8.

## Three layers (no monolith)

```
server.py   FastMCP surface — thin @mcp.tool wrappers, owns one HubSpotClient
   │ delegates to
tools.py    pure, traced functions; normalize to the schema; idempotency lives here
   │ uses an injected
client.py   HubSpotClient (httpx) — the ONLY thing that touches the HubSpot network
```

Tools depend on the `HubSpotClientProtocol` interface (`get` / `post`), not the
concrete client, so tests and the contract eval inject a fake and run with **no token
and no network**. Because the logic is in pure functions, the orchestrator calls
`tools.read_contacts(...)` directly — it does not need to go through MCP (Part 12 keeps
the business logic reusable).

## Tool surface

```python
from ruvu_sdr.mcp_servers.hubspot import tools
from ruvu_sdr.mcp_servers.hubspot.client import HubSpotClient

c = HubSpotClient()                                  # token from Settings/.env
tools.read_contacts(c, limit=10, after=None)         # -> ContactsPage
tools.read_company(c, company_id)                    # -> Company | None  (None on 404)
tools.log_activity(c, contact_id, body, idem_key)    # -> ActivityResult  (idempotent)
```

| Tool | HubSpot endpoint | Returns |
|---|---|---|
| `read_contacts(limit, after)` | `GET /crm/v3/objects/contacts` | `ContactsPage` |
| `read_company(company_id)` | `GET /crm/v3/objects/companies/{id}` | `Company` or `None` (404) |
| `log_activity(contact_id, body, idempotency_key)` | `POST /crm/v3/objects/notes` (+ association) | `ActivityResult` |

## Return shapes (normalized to the Part 10 schema, not raw HubSpot JSON)

Reads are mapped to the `contacts` table columns so the orchestrator stays decoupled
from HubSpot's property names (`firstname` -> `first_name`, `jobtitle` -> `title`, ...).

```python
Contact(hubspot_id, email, first_name, last_name, title, company)
ContactsPage(contacts: list[Contact], next_after: str | None)   # cursor; None at end
Company(hubspot_id, name, domain, industry)
ActivityResult(engagement_id, created: bool, idempotent_hit: bool)
```

## Idempotency (two layers)

`log_activity` is safe to retry — no double-logged note (Part 4 rule 5):

1. **MCP layer (here):** a hidden marker `<!--ruvu-idem:{idempotency_key}-->` is
   embedded in the note body. Before posting, the tool reads the contact's existing
   notes (associations + batch-read) and scans for the marker; on a hit it returns the
   existing note with `created=False, idempotent_hit=True` and posts nothing. This is a
   raw-body scan, so it does not depend on HubSpot's full-text search tokenization.
2. **Orchestrator layer (later):** the Postgres `touches.idempotency_key` UNIQUE
   constraint is the second guard, wired when the orchestrator calls this.

## Errors

The client raises `HubSpotError(status, message)` on any non-2xx, so callers never see
a raw `httpx` exception. `read_company` inspects `status` to turn a 404 into `None`;
any other status propagates.

## Tracing

Each tool is wrapped in `@observe` and tags the span (`tool`, `contact_id`, ...). As
with the Context API, tracing is a no-op when no Langfuse keys are configured, so tests
and the eval run untraced. Traces land when the tools run in a process that called
`configure_tracing()` — `server.py::main()` does this, and the orchestrator will too.

## Run the server

```bash
uv run python -m ruvu_sdr.mcp_servers.hubspot.server   # stdio FastMCP server
```

Needs `HUBSPOT_ACCESS_TOKEN` in `.env` (a HubSpot private-app token with contact/
company read and note write scopes). See `.env.example`.

## The gate

The `hubspot_tool_contract` unit eval (golden set:
`golden_sets/hubspot_tool_contract.json`) runs on every PR: read tools return the
normalized shapes, `read_company` 404 -> `None`, and errors surface `HubSpotError`. The
behavioral checks (idempotency replay, the real client's error mapping via
`httpx.MockTransport`) live in `tests/test_hubspot_mcp.py`. Both run in CI.

```bash
uv run python -m ruvu_sdr.evals.runner --suite pr   # the gate
uv run pytest tests/test_hubspot_mcp.py             # the behavioral tests
```

## Extending

- **A new read field:** add the HubSpot property to the `_*_PROPERTIES` constant in
  `tools.py` and the field to the relevant pydantic model + normalizer.
- **A new tool:** add a pure function in `tools.py`, wrap it in `server.py`, and add a
  contract case to the golden set. The injected-client pattern keeps it testable.
