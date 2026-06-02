-- 001_init.sql — initial schema (playbook Part 10), applied by scripts/run_migrations.py.
-- The table DDL below is verbatim from Part 10 so it can be diffed against the playbook.
-- pgvector is enabled now so the Plane 05 vector layer (Part 9) is ready when needed.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hubspot_id      TEXT UNIQUE NOT NULL,
    email           TEXT NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    title           TEXT,
    company         TEXT,
    state           TEXT NOT NULL DEFAULT 'NEW',
    enriched_data   JSONB,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE enrichment_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID REFERENCES contacts(id),
    clay_row_id     TEXT,
    status          TEXT DEFAULT 'PENDING',  -- PENDING | COMPLETE | FAILED | TIMEOUT
    submitted_at    TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE TABLE touches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID REFERENCES contacts(id),
    touch_number    INT NOT NULL,
    channel         TEXT DEFAULT 'email',
    subject         TEXT,
    body            TEXT,
    gmail_message_id TEXT,
    sent_at         TIMESTAMPTZ,
    idempotency_key TEXT UNIQUE NOT NULL  -- contact_id + touch_number, prevents double-send
);

CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID REFERENCES contacts(id),
    direction       TEXT NOT NULL,   -- inbound | outbound
    body            TEXT,
    intent          TEXT,            -- interested | not_interested | objection | ooo | unsubscribe | other
    intent_confidence NUMERIC,       -- for drift monitoring
    human_corrected_intent TEXT,     -- the eval signal: did a human override the classifier
    gmail_message_id TEXT UNIQUE,
    received_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE approvals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID REFERENCES contacts(id),
    kind            TEXT NOT NULL,   -- first_touch | nudge | reply
    proposed_subject TEXT,
    proposed_body   TEXT,
    status          TEXT DEFAULT 'PENDING',  -- PENDING | APPROVED | REJECTED | EDITED
    final_body      TEXT,            -- human edits land here (also an eval signal)
    decided_at      TIMESTAMPTZ
);

CREATE TABLE meetings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID REFERENCES contacts(id),
    calcom_booking_id TEXT UNIQUE,
    scheduled_for   TIMESTAMPTZ,
    status          TEXT DEFAULT 'BOOKED',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Episodic memory: past traces and outcomes, read via ctx.recall()
CREATE TABLE episodic_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type       TEXT NOT NULL,   -- first_touch | nudge | reply
    input_summary   JSONB,
    output          TEXT,
    outcome         TEXT,            -- replied | booked | ignored | unsubscribed
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Eval harness: case store
CREATE TABLE eval_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension       TEXT NOT NULL,   -- unit | component | system | adversarial | fairness
    eval_name       TEXT NOT NULL,   -- email_quality | reply_intent | injection_suite ...
    input           JSONB,
    expected        JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE eval_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_name       TEXT NOT NULL,
    git_sha         TEXT,
    score           NUMERIC,
    passed          BOOLEAN,
    detail          JSONB,
    run_at          TIMESTAMPTZ DEFAULT now()
);
