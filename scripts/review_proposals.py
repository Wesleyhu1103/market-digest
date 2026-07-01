#!/usr/bin/env python3
"""Review clustered feedback proposals — list, approve, reject, or view raw feedback.

Uses scripts/feedback_db.mjs for Postgres I/O.
Run: POSTGRES_URL=... python3 scripts/review_proposals.py list
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_CLI = ROOT / "scripts" / "feedback_db.mjs"


def db_cmd(*args: str) -> object:
    proc = subprocess.run(
        ["node", str(DB_CLI), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "feedback_db.mjs failed")
    return json.loads(proc.stdout or "null")


def fmt_date(val) -> str:
    if not val:
        return "?"
    if isinstance(val, str):
        return val[:10]
    return str(val)[:10]


def print_proposal(p: dict) -> None:
    print(f"ID {p['id']}  [{p['category']}]  {p['status']}  votes={p.get('vote_count', 0)}")
    print(f"  Title: {p['title']}")
    if p.get("summary"):
        print(f"  Summary: {p['summary']}")
    if p.get("reject_reason"):
        print(f"  Reject reason: {p['reject_reason']}")
    sources = p.get("sources") or []
    if sources:
        print("  Sources:")
        for s in sources:
            excerpt = (s.get("text") or "")[:120]
            if len(s.get("text") or "") > 120:
                excerpt += "…"
            print(f"    - \"{excerpt}\" ({fmt_date(s.get('date'))})")
    print()


def cmd_list(args: argparse.Namespace) -> None:
    status = args.status or "pending"
    rows = db_cmd("list-proposals", status)
    if not rows:
        print(f"No proposals with status={status!r}.")
        return
    print(f"{len(rows)} proposal(s) [{status}]:\n")
    for p in rows:
        print_proposal(p)


def cmd_raw(args: argparse.Namespace) -> None:
    days = None
    if args.since:
        m = {"d": 1, "w": 7}.get(args.since[-1].lower())
        if m and args.since[:-1].isdigit():
            days = int(args.since[:-1]) * m
        elif args.since.endswith("d") and args.since[:-1].isdigit():
            days = int(args.since[:-1])
    rows = db_cmd("raw", str(days)) if days else db_cmd("raw")
    if not rows:
        print("No raw feedback found.")
        return
    print(f"{len(rows)} raw submission(s):\n")
    for r in rows:
        text = " | ".join(filter(None, [r.get("missing"), r.get("open")]))
        proc = "processed" if r.get("processed_at") else "unprocessed"
        print(f"#{r['id']}  {fmt_date(r.get('digest_date') or r.get('created_at'))}  [{proc}]")
        print(f"  {text[:200]}{'…' if len(text) > 200 else ''}")
        print()


def cmd_approve(args: argparse.Namespace) -> None:
    if not args.ids:
        raise SystemExit("Usage: review_proposals.py approve ID [ID ...]")
    ids = [str(i) for i in args.ids]
    result = db_cmd("approve", *ids)
    print(f"Approved {len(result.get('approved', []))} proposal(s): {result.get('approved')}")


def cmd_reject(args: argparse.Namespace) -> None:
    if not args.ids:
        raise SystemExit("Usage: review_proposals.py reject ID [ID ...] [--reason TEXT]")
    cmd = ["reject", *[str(i) for i in args.ids]]
    if args.reason:
        cmd.extend(["--reason", args.reason])
    result = db_cmd(*cmd)
    print(f"Rejected {len(result.get('rejected', []))} proposal(s): {result.get('rejected')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Review feedback proposals")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List proposals (default: pending)")
    p_list.add_argument("--status", default="pending", help="pending|approved|rejected|done")
    p_list.set_defaults(func=cmd_list)

    p_raw = sub.add_parser("raw", help="View raw feedback submissions")
    p_raw.add_argument("--since", default="7d", help="e.g. 7d, 14d")
    p_raw.set_defaults(func=cmd_raw)

    p_app = sub.add_parser("approve", help="Approve proposals for public voting")
    p_app.add_argument("ids", nargs="+", type=int)
    p_app.set_defaults(func=cmd_approve)

    p_rej = sub.add_parser("reject", help="Reject proposals")
    p_rej.add_argument("ids", nargs="+", type=int)
    p_rej.add_argument("--reason", default=None)
    p_rej.set_defaults(func=cmd_reject)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
