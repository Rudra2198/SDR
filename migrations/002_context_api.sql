-- 002_context_api.sql — backing stores for the Context API live layers (Plane 05, playbook Part 3).
-- Applied by scripts/run_migrations.py. Plain SQL, no ORM (Parts 4, 12).
--
-- Adds:
--   * tenant_prefs            — the user/session layer's store (ctx.user_prefs), tenant-scoped.
--   * semantic_contact_funnel — typed metric: contact counts by lifecycle state.
--   * semantic_reply_rate     — typed metric: replied / sent (0 until the send path lands).
-- The semantic layer reads Postgres VIEWS (Part 3: "Postgres views, later Cube / dbt MetricFlow"),
-- so the metric SQL is governed in one place and swappable without touching agent code.

-- ─── User / session layer (LIVE) ──────────────────────────────────────────────
CREATE TABLE tenant_prefs (
    tenant_id   TEXT PRIMARY KEY,
    prefs       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ruvu's own tone + brand rules (Part 3, Part 4 rule 9). No em-dashes in this seed copy either.
INSERT INTO tenant_prefs (tenant_id, prefs) VALUES (
    'ruvu',
    '{
        "voice": "warm, relationship-first, concise",
        "rules": [
            "no em-dashes; use commas, parentheses, periods",
            "one clear single ask per email",
            "personalize using real enriched data, never generic flattery",
            "keep it short, under 120 words"
        ],
        "signature": "Ash, Ruvu",
        "sender_name": "Ash"
    }'::jsonb
);

-- ─── Semantic layer (LIVE) — typed metrics as Postgres views ───────────────────
-- contact_funnel: how many contacts sit in each lifecycle state right now.
CREATE VIEW semantic_contact_funnel AS
SELECT state, count(*)::bigint AS n
FROM contacts
GROUP BY state;

-- reply_rate: distinct contacts that replied over distinct contacts we have sent to.
-- Returns value 0 with replied = sent = 0 until the send path (Phase 3) produces data.
CREATE VIEW semantic_reply_rate AS
WITH sent AS (
    SELECT DISTINCT contact_id FROM touches WHERE sent_at IS NOT NULL
),
replied AS (
    SELECT DISTINCT contact_id FROM conversations WHERE direction = 'inbound'
)
SELECT
    (SELECT count(*) FROM replied)::bigint AS replied,
    (SELECT count(*) FROM sent)::bigint    AS sent,
    COALESCE(
        (SELECT count(*) FROM replied)::numeric
            / NULLIF((SELECT count(*) FROM sent), 0),
        0
    ) AS value;
