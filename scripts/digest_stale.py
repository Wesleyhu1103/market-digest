#!/usr/bin/env python3
"""Return whether docs/index.html is behind today's US/Eastern digest date."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest_date import digest_date

INDEX = Path(__file__).resolve().parents[1] / "docs" / "index.html"


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
