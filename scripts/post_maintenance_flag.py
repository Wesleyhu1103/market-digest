#!/usr/bin/env python3
"""Post a site-maintenance flag to /api/maintenance (monitor -> admin board).

Usage:
  post_maintenance_flag.py --source feed-check --title "..." \
      [--detail "..."] [--severity warning] [--url https://...] [--dedupe-key k]

Auth comes from the MAINTENANCE_TOKEN env var; exits 0 with a notice when it
is unset so monitors never fail their own runs over flag delivery.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

ATTEMPTS = 3

ENDPOINT = os.environ.get(
    "MAINTENANCE_ENDPOINT", "https://market-digest-liart.vercel.app/api/maintenance"
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--detail", default=None)
    p.add_argument("--severity", default="warning", choices=["critical", "warning", "info"])
    p.add_argument("--url", default=None)
    p.add_argument("--dedupe-key", default=None)
    args = p.parse_args()

    token = os.environ.get("MAINTENANCE_TOKEN", "")
    if not token:
        print("MAINTENANCE_TOKEN not set; skipping maintenance flag post")
        return 0

    body = {
        "source": args.source,
        "title": args.title,
        "severity": args.severity,
    }
    if args.detail:
        body["detail"] = args.detail
    if args.url:
        body["url"] = args.url
    if args.dedupe_key:
        body["dedupeKey"] = args.dedupe_key

    for attempt in range(1, ATTEMPTS + 1):
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-maintenance-token": token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                print("maintenance flag posted:", res.read().decode()[:200])
                return 0
        except (OSError, urllib.error.URLError) as e:
            # Never fail the calling monitor over flag delivery.
            if attempt < ATTEMPTS:
                print(f"maintenance flag POST attempt {attempt}/{ATTEMPTS} failed, retrying: {e}")
                time.sleep(2 * attempt)
            else:
                print("maintenance flag POST failed (non-fatal):", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
