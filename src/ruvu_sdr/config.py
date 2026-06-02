"""Typed application settings, loaded from environment / `.env`.

Single source of configuration truth (Plane 07 governance). Import the cached
`get_settings()` accessor rather than constructing `Settings` directly.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings. Unknown env vars are ignored."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── Database (Planes 05/06) ──────────────────────────────────
    database_url: str = "postgresql://ruvu:ruvu@localhost:5432/ruvu_sdr"

    # ─── Langfuse (Plane 07 observability) ────────────────────────
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://us.cloud.langfuse.com"

    # ─── Anthropic (Plane 03 agents) — needed from Phase 2 ────────
    anthropic_api_key: str | None = None

    @property
    def langfuse_configured(self) -> bool:
        """True when both Langfuse keys are present (tracing can be flushed)."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached settings instance."""
    return Settings()
