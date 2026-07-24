#!/usr/bin/env python3
"""Return whether the digest is behind today's US/Eastern date.

Default: checks the local checkout's docs/index.html. With --remote URL it
checks the live page instead (e.g. raw.githubusercontent.com main) so a
long-lived run can re-verify against reality before alarming; if the remote
fetch fails, it falls back to the local file so uncertainty reads as stale
(alarm) rather than silently current.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest_date import digest_date

INDEX = Path(__file__).resolve().parents[1] / "docs" / "index.html"


def load_html(remote: str | None) -> str:
    if remote:
        try:
            with urllib.request.urlopen(remote, timeout=30) as res:
                return res.read().decode("utf-8", "replace")
        except (OSError, urllib.error.URLError) as e:
            print(f"remote fetch failed ({e}); falling back to local index.html")
    return INDEX.read_text()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--remote", default=None, help="check this URL instead of the local file")
    args = p.parse_args()

    html = load_html(args.remote)
    found = digest_date(html)
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    if not found:
        print(f"today={today} digest_date=unknown stale=true")
        return 1
    stale = found < today
    print(f"today={today} digest_date={found} stale={'true' if stale else 'false'}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
