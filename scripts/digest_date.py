"""Parse the digest edition date from index.html content."""
from __future__ import annotations

import re
from datetime import datetime


def digest_date(html: str) -> str | None:
    """Return YYYY-MM-DD for the edition, or None if not found."""
    meta = re.search(r"date:\s*'(\d{4}-\d{2}-\d{2})'", html)
    if meta:
        return meta.group(1)
    h1 = re.search(r"<h1>([^<]+)</h1>", html)
    if not h1:
        return None
    try:
        return datetime.strptime(h1.group(1).strip(), "%A, %B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None
