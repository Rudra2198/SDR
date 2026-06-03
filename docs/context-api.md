# The Context API (Plane 05, the moat)

One tenant-scoped interface over six context layers with a fixed return shape, every
method traced. Agents never touch a data store directly for context (playbook Part 4
rule 3); they call this. Swapping a stubbed layer for a real one later does not touch
a single line of agent code. Spec: [`ruvu-sdr-agent-playbook.md`](../ruvu-sdr-agent-playbook.md) Part 3.

## Surface

```python
from ruvu_sdr.context_api import ContextAPI

ctx = ContextAPI()                       # defaults to tenant 'ruvu'
ctx.metric("contact_funnel")             # semantic — LIVE
ctx.metric("reply_rate")                 # semantic — LIVE
ctx.recall("first_touch")                # episodic — LIVE
ctx.user_prefs()                         # user     — LIVE
ctx.graph_path(a, b)                     # graph    — raises NotImplementedForTenant
ctx.search(query, k=5)                   # vector   — raises NotImplementedForTenant
ctx.doc(uri)                             # document — raises NotImplementedForTenant
```

| Method | Layer | v1 | Backing store |
|---|---|---|---|
| `metric(name, slice)` | semantic | LIVE | Postgres views (`semantic_contact_funnel`, `semantic_reply_rate`) |
| `recall(task_type, limit)` | episodic | LIVE | `episodic_memory` table |
| `user_prefs()` | user/session | LIVE | `tenant_prefs` table |
| `graph_path(a, b)` | knowledge graph | STUBBED | raises `NotImplementedForTenant` |
| `search(query, k)` | vector | STUBBED | raises `NotImplementedForTenant` |
| `doc(uri)` | document | STUBBED | raises `NotImplementedForTenant` |

The stubbed methods are **registered and real**, not missing. They exist, they trace,
and they raise a clean `NotImplementedForTenant`. The interface is complete; only the
backing is deferred.

## Return shape

Every live method returns the same envelope, so callers get one shape regardless of
the store behind it:

```python
ContextResult(
    layer,       # Layer enum: semantic | episodic | user | ...
    tenant_id,   # the tenant this read was scoped to
    query,       # the method args, echoed back for traceability
    data,        # the payload, shaped by the layer
    source,      # backing-store id, e.g. "postgres:semantic_reply_rate"
)
```

## Tracing

Each method is wrapped in `@observe` and tags the current span (via
`observability.tag_observation`) with `tenant_id` and `layer` (Part 4 rule 7: "if it
is not traced, it did not happen"). With no Langfuse keys present, tracing is a no-op,
so tests and fresh checkouts run without it.

Verified end to end against Langfuse Cloud (traces read back via the API, not just
sent): every method emits one observation named `ctx.<method>` carrying
`metadata.tenant_id` and `metadata.layer`, so traces are filterable by tenant and by
context layer. The three **stubbed** layers trace too and surface as
`level=ERROR` (the `NotImplementedForTenant` raise is captured), so a stubbed-layer
call is visible and flagged in observability, never silent.

To reproduce, exercise a `ctx` call inside a configured trace and confirm it lands:

```bash
uv run python scripts/check_langfuse.py   # the Phase 0 smoke path (@observe -> trace)
```

## Tenant scoping

`ContextAPI(tenant_id=...)` carries a tenant through every method and trace; it
defaults to `"ruvu"`. v1 is single-tenant, so the live stores are not yet
tenant-partitioned and `NotImplementedForTenant` is raised for every tenant. The
interface is already multi-tenant-shaped; a second tenant adds rows/partitions to the
live layers without changing agent code.

## Extending

- **A new metric:** add a Postgres view in a migration, then register a resolver in
  `context_api/layers/semantic.py::_METRICS`. Nothing else changes.
- **Implementing a stub:** replace the `raise` in the relevant `ContextAPI` method
  with a layer call that returns a `ContextResult`. Upstream callers are unaffected.

## The gate

The `context_api_contract` unit eval (golden set: `golden_sets/context_api_contract.json`)
runs on every PR: live methods must return the envelope with the right layer; stubbed
methods must raise `NotImplementedForTenant`. This is the first eval with real cases, so
the PR gate now has teeth. Run it:

```bash
uv run python -m ruvu_sdr.evals.runner --suite pr
```
