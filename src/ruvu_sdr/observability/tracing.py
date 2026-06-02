"""Plane 07 — Langfuse tracing.

Every Claude call and every Context API call gets traced (Part 4, rule 7: "if it
is not traced, it did not happen"). This module centralizes Langfuse setup so the
rest of the codebase just imports `observe` and decorates.

Tracing configures from settings (`.env`). When the keys are absent — e.g. in unit
tests or a fresh checkout — tracing is disabled and `@observe` becomes a no-op, so
nothing breaks without credentials.
"""

from __future__ import annotations

from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe

from ruvu_sdr.config import get_settings

__all__ = [
    "observe",
    "configure_tracing",
    "current_trace_url",
    "flush",
    "get_client",
    "tracing_enabled",
]


def tracing_enabled() -> bool:
    """True when both Langfuse keys are present."""
    return get_settings().langfuse_configured


def configure_tracing() -> bool:
    """Configure the global Langfuse context from settings.

    Returns True if tracing is enabled (keys present), False if disabled. Safe to
    call more than once. Call this once at process start before any traced code.
    """
    settings = get_settings()
    if not settings.langfuse_configured:
        langfuse_context.configure(enabled=False)
        return False
    langfuse_context.configure(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        enabled=True,
    )
    return True


def get_client() -> Langfuse:
    """Return a configured Langfuse client (for direct, non-decorator use)."""
    settings = get_settings()
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def current_trace_url() -> str | None:
    """URL of the trace currently in scope. Call inside an `@observe` function."""
    try:
        return langfuse_context.get_current_trace_url()
    except Exception:
        return None


def flush() -> None:
    """Flush buffered events. Always call before a short-lived process exits."""
    langfuse_context.flush()
