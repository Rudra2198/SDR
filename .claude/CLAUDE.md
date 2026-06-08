# CLAUDE.md

Project context for Claude Code. The authoritative spec is
[`ruvu-sdr-agent-playbook.md`](./ruvu-sdr-agent-playbook.md); when in doubt, defer to it.

## What this is

Ruvu's own outbound SDR (Sales Development Representative) agent, built as a faithful miniature
of the full Ruvu reference architecture. "Eat the cooking": we sell agentic GTM systems, so our
own outbound runs as one. The agent reads HubSpot through a governed Context API, enriches via
Clay, writes and sends personalized email behind a human approval gate, classifies replies,
nudges non-responders, books meetings, logs back to HubSpot, traces every step in Langfuse, and
gates every change on an eval substrate.

Built **phase by phase** (playbook Part 13), not feature by feature. This is core IP: build like
someone else will read and reuse every line.

## Architecture: the seven planes (Part 2)

| Plane | What | Where in code | Status |
|---|---|---|---|
| 01 Interaction | Approval queue, ops dashboard, reply webhooks | (later) | planned |
| 02 Orchestration | Deterministic state machine + APScheduler loop | `src/ruvu_sdr/orchestrator/` | Phase 1+ |
| 03 Capability | 3 Claude judgment steps (write, classify, draft) | `src/ruvu_sdr/agents/` | Phase 2+ |
| 04 Tooling / MCP | hubspot, clay, gmail, calcom (FastMCP) | `src/ruvu_sdr/mcp_servers/` | Phase 1+ |
| 05 Context Layer | The Context API, 6 layers (the moat) | `src/ruvu_sdr/context_api/` | Phase 1 |
| 06 Data systems | Postgres, HubSpot, Gmail, Cal.com | `migrations/`, `src/ruvu_sdr/db.py` | live |
| 07 Governance | Evals, Langfuse, approval gate | `src/ruvu_sdr/evals/`, `observability/` | live |

## Principles you do not get to violate (Part 4)

1. **Deterministic skeleton, agent muscles.** Control flow (send, wait, branch, nudge) is plain
   code with explicit state. Claude is called ONLY for judgment. A loop and a timestamp decide
   "wait 3 days," never an LLM.
2. **All context goes through the Context API.** Agents never touch a data store directly for
   context.
3. **State lives in Postgres.** Every contact, touch, reply, job, approval is a row. Crash and
   restart resumes exactly where it left off.
4. **The approval gate is a feature, not a phase.** Every outbound email routes through human
   approval in v1. We graduate off it on eval evidence, never rip it out.
5. **Idempotency everywhere.** Unique keys, check before act. No double-sends on retry.
6. **Everything is traced.** Langfuse on every Claude call and Context API call. If it is not
   traced, it did not happen.
7. **Nothing merges without passing the eval gate.** CI runs the harness on every PR.
8. **No em-dashes in generated email copy.** Commas, parentheses, periods. Brand rule.

## Eval-first SDLC (Parts 5, 6, 15)

The eval exists **before** the code it judges. For each agent step: write its capability card,
then its golden set plus rubric, then the code, then tune until the eval passes. One PR per
slice; merge only on green CI. The orchestrator comes last in each subsystem, after the pieces
it calls already work in isolation.

## Stack (locked, Part 9)

Python 3.12 via **uv** · Postgres 16 + pgvector (Docker) · FastMCP · Anthropic SDK (judgment
only) · Langfuse · ruff + pre-commit · pytest · GitHub Actions. No ORM and no Temporal in v1;
durability comes from Postgres, migrations are plain versioned SQL.

## Commands

```bash
uv sync                                              # install deps (provisions Python 3.12)
docker compose up -d                                 # start Postgres (needs Docker running)
uv run python scripts/run_migrations.py              # apply migrations (idempotent)
uv run ruff check . && uv run ruff format .          # lint + format
uv run pytest                                        # tests
uv run python -m ruvu_sdr.evals.runner --suite pr    # the CI eval gate
uv run python scripts/check_langfuse.py              # confirm a Langfuse trace lands
```

Secrets live in `.env` (gitignored); see `.env.example`. The Langfuse host var is `LANGFUSE_HOST`.

## Workflow conventions

- Branch per slice, PR into `main` (protected: PR review plus green `ci` check required). Delete
  merged branches.
- Commit after every passing gate.
- Keep business logic in pure functions (`draft_email`, `classify_reply`, `book_meeting`) that
  the orchestrator loop calls, so the Temporal path stays open later (Part 12).

## Status

**Phase 0 (Foundations): complete.** Next: **Phase 1**, the Context API (6 methods, 3 live and
3 cleanly stubbed), `hubspot-mcp`, `clay-mcp` (async submit/fetch, Part 7), and a tiny
orchestrator that takes contacts NEW to ENRICHED.
