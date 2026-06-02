"""Plane 02 — Orchestration.

The deterministic state machine that advances each contact through the lifecycle
(NEW → ENRICHING → ... → MEETING_BOOKED), driven by an APScheduler loop reading
Postgres. No LLM decides control flow. Built from Phase 1 onward.
"""
