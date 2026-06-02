"""Phase 0 smoke test: confirm a Langfuse trace lands.

Configures tracing from `.env`, emits a traced span through the `@observe`
decorator (the same path app code will use for Claude / Context API calls),
flushes, and prints the trace URL.

    uv run python scripts/check_langfuse.py
"""

from __future__ import annotations

import sys

from ruvu_sdr.observability import configure_tracing, current_trace_url, flush, observe


@observe(name="phase0-smoke-test")
def _smoke(message: str) -> str | None:
    # Stands in for a future Claude / Context API call. Returns the trace URL so
    # the caller can confirm it landed.
    return current_trace_url()


def main() -> int:
    if not configure_tracing():
        print("Langfuse not configured: set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
        print("in .env (see .env.example), then re-run.")
        return 1

    url = _smoke("phase-0 foundations")
    flush()  # short-lived process: flush before exit or the event is lost

    print("Emitted a trace via @observe (name='phase0-smoke-test').")
    if url:
        print(f"View it here: {url}")
    else:
        print("Trace sent; open Langfuse → Traces → 'phase0-smoke-test' to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
