#!/usr/bin/env python3
"""Return whether docs/index.html is behind today's US/Eastern digest date."""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

INDEX = Path(__file__).resolve().parents[1] / "docs" / "index.html"


def digest_date(html: str) -> str | None:
    m = re.search(r"date:\s*'(\d{4}-\d{2}-\d{2})'", html)
    if m:
        return m.group(1)
    h1 = re.search(r"<h1>([^<]+)</h1>", html)
    if not h1:
        return None
    try:
        return datetime.strptime(h1.group(1).strip(), "%A, %B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def main() -> int:
    html = INDEX.read_text()
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
