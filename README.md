# Ruvu Outbound SDR Agent

Ruvu's own outbound SDR motion, built as a faithful miniature instance of the full Ruvu
reference architecture. "Eat the cooking": we sell agentic GTM systems, so our own outbound
runs as one. See [`ruvu-sdr-agent-playbook.md`](./ruvu-sdr-agent-playbook.md) for the full brief.

An autonomous agent reads HubSpot through a governed **Context API**, enriches via Clay,
writes and sends personalized outbound (behind a human approval gate), classifies replies,
nudges, books meetings, logs back to HubSpot, traces every step in Langfuse, and gates every
change on an eval substrate.

## Architecture planes (Part 2 of the playbook)

| Plane | In this build | Status |
|---|---|---|
| 01 Interaction | Approval queue + ops dashboard; inbound reply webhooks | later |
| 02 Orchestration | Deterministic state machine (`src/ruvu_sdr/orchestrator/`) | Phase 1+ |
| 03 Capability | Three Claude judgment steps (`src/ruvu_sdr/agents/`) | Phase 2+ |
| 04 Tooling / MCP | hubspot, clay, gmail, calcom (`src/ruvu_sdr/mcp_servers/`) | Phase 1+ |
| 05 Context Layer | The Context API, 6 layers (`src/ruvu_sdr/context_api/`) | Phase 1 |
| 06 Data systems | Postgres, HubSpot, Gmail, Cal.com | Phase 0+ |
| 07 Governance | Eval substrate (`src/ruvu_sdr/evals/`), Langfuse, approval gate | **Phase 0** |

## Stack

Python 3.12 (managed by [uv]) · Postgres 16 + pgvector (Docker) · Langfuse · ruff · pytest ·
GitHub Actions. Tech stack is locked in Part 9 of the playbook.

## Quickstart

```bash
# 1. Install deps into a managed venv (provisions Python 3.12 automatically)
uv sync

# 2. Configure environment
cp .env.example .env        # then fill in Langfuse keys etc.

# 3. Start Postgres (needs Docker Desktop running)
docker compose up -d

# 4. Apply the schema (Part 10)
uv run python scripts/run_migrations.py

# 5. Run the checks
uv run ruff check .
uv run pytest
uv run python -m ruvu_sdr.evals.runner --suite pr   # the CI eval gate

# 6. Confirm a Langfuse trace lands (after keys are set)
uv run python scripts/check_langfuse.py
```

## Environment variables

See [`.env.example`](./.env.example). `DATABASE_URL` and the `LANGFUSE_*` keys are needed for
Phase 0; `ANTHROPIC_API_KEY` and tool credentials come online in later phases.

## Development discipline (Parts 5, 6, 15)

Build **phase by phase**, not feature by feature. Each agent step gets a capability card and an
eval (golden set + rubric) **before** the code it judges. Open a PR per slice; CI runs the eval
gate; merge only on green. Nothing auto-sends in v1 — every outbound email goes through human
approval, and we graduate off the gate only when evals prove quality.

[uv]: https://docs.astral.sh/uv/
