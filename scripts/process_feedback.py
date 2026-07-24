#!/usr/bin/env python3
"""Cluster unprocessed reader feedback into pending proposals for editor review.

Local/manual path only — CI (process-feedback.yml) goes through the deployed
admin API via scripts/call_admin_api.py instead, so the runner needs no DB URL.

Uses scripts/feedback_db.mjs for Postgres I/O (postgres npm package already in repo).
Run: SUPABASE_DB_URL=... python3 scripts/process_feedback.py
(POSTGRES_URL and DATABASE_URL are accepted as fallbacks; see api/_supa.js.)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_CLI = ROOT / "scripts" / "feedback_db.mjs"


def main() -> int:
    proc = subprocess.run(
        ["node", str(DB_CLI), "process"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "feedback_db.mjs process failed")
    result = json.loads(proc.stdout or "{}")
    print(result.get("message") or json.dumps(result))
    if result.get("proposals"):
        for p in result["proposals"]:
            print(f"  proposal #{p['id']} [{p['category']}] {p['title']} ({p['sources']} source(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
