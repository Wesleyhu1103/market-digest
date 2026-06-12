#!/usr/bin/env python3
"""Fail if docs/fred-data.json macro series are too stale."""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "fred-data.json"
MAX_STALE_DAYS = 4
REQUIRE_KEY = os.environ.get("REQUIRE_FRED_API_KEY", "").lower() in {"1", "true", "yes"}


def main() -> int:
    if REQUIRE_KEY and not os.environ.get("FRED_API_KEY"):
        print("ERROR: FRED_API_KEY secret not set (required for fresh macro charts)")
        return 1

    try:
        payload = json.loads(OUT.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read {OUT}: {e}")
        return 1

    today = date.today()
    checks = [
        ("DGS10", payload.get("fred", {}).get("DGS10", [])),
        ("Brent", payload.get("brent", [])),
        ("HY_OAS", payload.get("credit", {}).get("HY_OAS", [])),
    ]
    problems = []
    for name, series in checks:
        if not series:
            problems.append(f"{name}: no data")
            continue
        last = datetime.strptime(series[-1]["date"], "%Y-%m-%d").date()
        age = (today - last).days
        if age > MAX_STALE_DAYS:
            problems.append(f"{name}: last point {last} ({age}d old)")

    updated = payload.get("updated", "unknown")
    print(f"fred-data.json updated {updated}")
    if problems:
        for p in problems:
            print(f"STALE: {p}")
        if os.environ.get("FRED_API_KEY"):
            return 1
        print("WARN: FRED_API_KEY not set; allowing stale macro data")
    else:
        print("OK: macro series within freshness window")
    return 0


if __name__ == "__main__":
    sys.exit(main())
