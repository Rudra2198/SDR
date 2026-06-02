"""Apply pending SQL migrations in filename order, idempotently.

Applied files are recorded in a `schema_migrations` table; each migration runs in
its own transaction and is skipped if already applied. Plain SQL, no ORM
(playbook Parts 4 and 12). Safe to re-run.

    uv run python scripts/run_migrations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from ruvu_sdr.db import connect

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

ENSURE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _applied(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM schema_migrations;")
        return {row["filename"] for row in cur.fetchall()}


def main() -> int:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print(f"No migrations found in {MIGRATIONS_DIR}")
        return 0

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(ENSURE_TRACKING_TABLE)
        conn.commit()

        done = _applied(conn)
        pending = [f for f in files if f.name not in done]

        if not pending:
            print(f"Up to date — {len(done)} migration(s) already applied.")
            return 0

        for f in pending:
            print(f"Applying {f.name} ...", end=" ", flush=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(f.read_text())
                    cur.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s);",
                        (f.name,),
                    )
                conn.commit()
                print("ok")
            except Exception:
                conn.rollback()
                print("FAILED (rolled back)")
                raise

        print(f"Done — applied {len(pending)} migration(s).")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
