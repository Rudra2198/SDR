# Phase 0 → Phase 1 Handoff

Status snapshot for resuming work on the Ruvu SDR agent. A new Claude Code session in this repo
auto-loads [`CLAUDE.md`](../CLAUDE.md) (architecture, principles, commands); this doc adds what
Phase 0 delivered, the current state, and exactly what Phase 1 is. Source of truth:
[`ruvu-sdr-agent-playbook.md`](../ruvu-sdr-agent-playbook.md).

## Project
Ruvu's outbound SDR agent in `/Users/rudra/CC_Workspace/SDR`, a faithful miniature of the
7-plane Ruvu reference architecture, built **phase by phase**. Repo:
`github.com/Rudra2198/SDR` (public). **Phase 0 is complete and merged to `main`.**

## What Phase 0 delivered (all merged to `main`, CI green)
- **Project scaffold**: `uv` + Python 3.12, `src/` layout (`src/ruvu_sdr/`), `pyproject.toml`,
  `ruff` + `pre-commit` (all hooks pass).
- **Postgres (Plane 06)**: Docker via `docker-compose.yml`, image `pgvector/pgvector:pg16`,
  container `ruvu_sdr_postgres` on `localhost:5432`. `migrations/001_init.sql` = Part 10 schema
  verbatim + `CREATE EXTENSION vector`. `scripts/run_migrations.py` = idempotent runner (tracks
  applied files in `schema_migrations`). 10 tables live, pgvector 0.8.2 enabled.
- **Eval substrate (Plane 07)** — the real deliverable, in `src/ruvu_sdr/evals/`:
  - `models.py` (`Case`, `ScoreResult`, `CaseResult`, `EvalResult`, `Dimension` StrEnum),
    `case_store.py` (`FileCaseStore` → `golden_sets/*.json`, `PostgresCaseStore`,
    `InMemoryCaseStore`), `scorers.py` (`Scorer` ABC + `ExactMatchScorer`), `registry.py`
    (`EvalSpec`, `REGISTRY`, `PR_SUITE`, suites `pr`/`nightly`), `runner.py` (`EvalRunner` + CLI).
  - CLI gate: `uv run python -m ruvu_sdr.evals.runner --suite pr` (0 cases now → passes; grows
    teeth as evals are registered). 4 unit tests pass.
- **Observability (Plane 07)**: `src/ruvu_sdr/observability/tracing.py` (`configure_tracing`,
  `observe`, `get_client`, `flush`, `current_trace_url`). `scripts/check_langfuse.py` smoke test
  with `auth_check`. Traces confirmed landing in Langfuse Cloud (US).
- **Core helpers**: `config.py` (pydantic-settings), `db.py` (psycopg3 `get_conn`/`get_cursor`,
  dict rows).
- **CI (Plane 07)**: `.github/workflows/ci.yml` — Postgres service (pgvector), `uv sync --frozen`,
  ruff check + format-check, migrations, pytest, eval gate. **Status check name is `ci`.**
- **Branch protection**: ruleset on `main` (PR review + `ci` required, no force-push/deletion,
  admin `pull_request` bypass). Repo made public to enable this for free (Pro is needed on private
  personal repos).
- **`CLAUDE.md`** committed (auto-loads project context).
- **Stub packages** for later: `context_api/` (05), `mcp_servers/` (04), `orchestrator/` (02),
  `agents/` (03) — docstrings only.

## Current state
- `main` only (no stale branches); latest commit is the CLAUDE.md merge.
- `.env` (gitignored) already has `DATABASE_URL`, `POSTGRES_*`, real
  `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`LANGFUSE_HOST` (US), and empty `ANTHROPIC_API_KEY`.
- `langfuse` pinned `<3` (v2 `@observe` API). Langfuse host var is `LANGFUSE_HOST`.

## Environment gotchas
- Use `uv run ...` for everything (`uv sync` provisions Python 3.12; system Python is 3.9).
- **Docker Desktop must be running** before `docker compose up -d`.
- `gh` CLI is authenticated (account `Rudra2198`).

## Key commands
```bash
uv sync
docker compose up -d
uv run python scripts/run_migrations.py
uv run ruff check . && uv run ruff format .
uv run pytest
uv run python -m ruvu_sdr.evals.runner --suite pr
uv run python scripts/check_langfuse.py
```

## Non-negotiables (playbook Part 4)
Deterministic skeleton + Claude for judgment only · all context via the Context API · state in
Postgres · idempotency · approval gate on every send · everything traced · no em-dashes in
generated email copy · nothing merges without the eval gate.

**Workflow**: branch per slice → PR → green CI → review → merge → delete branch. Commit after every
passing gate. **Eval-first**: capability card + golden set/rubric *before* the code it judges.

## NEXT: Phase 1 — Context API + read path (playbook Part 13, Part 3, Part 7)
Build, in order, each with unit tests + unit evals added to the harness:

1. **Context API** (`src/ruvu_sdr/context_api/`) — one tenant-scoped interface, six methods,
   consistent return shape, each emitting a Langfuse trace:
   - LIVE: `ctx.metric(name, slice)` (semantic / Postgres views), `ctx.recall(task_type)`
     (episodic / `episodic_memory` table), `ctx.user_prefs()` (user/session — Ruvu tone + brand
     rules).
   - STUBBED, raising `NotImplementedForTenant`: `ctx.graph_path(a, b)`, `ctx.search(query, k)`,
     `ctx.doc(uri)`.
2. **`hubspot-mcp`** (FastMCP) — read contacts/companies, write activity/notes.
3. **`clay-mcp`** (FastMCP, async per Part 7) — `submit_for_enrichment(contact) → clay_row_id`,
   `fetch_enrichment(clay_row_id) → data | pending`. 30-min timeout → mark TIMEOUT, proceed with
   HubSpot-only data.
4. **Tiny orchestrator** — pull `NEW` contacts → submit to Clay (→ `ENRICHING`) → on return land
   `ENRICHED`, writing enriched data into episodic/semantic memory **through the Context API**.

- **Artifact**: 5 real contacts pulled, enriched, in the DB, readable via the Context API.
- **Gate**: unit evals green.
- **New credentials needed**: HubSpot access token, Clay API key (+ webhook secret). Add to `.env`
  (slots are commented in `.env.example`).
