#!/usr/bin/env python3
"""Validate deal-source and dive-deeper links in the digest <main> block."""
from __future__ import annotations

import difflib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from feed_sources import UA, build_feed_url_index  # noqa: E402

PAYWALL_DOMAINS = ("bloomberg.com", "wsj.com", "ft.com")
LINK_RE = re.compile(
    r'(?:class="deal-source"|class="dive-deeper")[^>]*>.*?href="([^"]+)"[^>]*>([^<]+)',
    re.DOTALL,
)


def _normalize(url: str) -> str:
    return url.rstrip("/").split("#", 1)[0]


def _load_feed_index() -> dict[str, str]:
    return build_feed_url_index()


def _head_status(url: str) -> int | None:
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with opener.open(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (OSError, TimeoutError, urllib.error.URLError):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with opener.open(req, timeout=20) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code
        except (OSError, TimeoutError, urllib.error.URLError):
            return None


def _best_feed_match(label: str, feed_index: dict[str, str]) -> tuple[str, str, float] | None:
    outlet = ""
    if " -- " in label:
        outlet = label.split(" -- ", 1)[0].replace("Source:", "").strip().lower()
    headline = label.split(" -- ", 1)[-1].strip().lower()
    best: tuple[str, str, float] | None = None
    for url, title in feed_index.items():
        domain_ok = not outlet or outlet in url.lower() or (
            outlet == "bloomberg" and "bloomberg.com" in url
        ) or (outlet == "coindesk" and "coindesk.com" in url) or (
            outlet == "cnbc" and "cnbc.com" in url
        )
        if not domain_ok:
            continue
        score = difflib.SequenceMatcher(None, headline, title.lower()).ratio()
        if best is None or score > best[2]:
            best = (url, title, score)
    return best


def extract_links(main_html: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2).strip()) for m in LINK_RE.finditer(main_html)]


def validate_main(main_html: str, feed_index: dict[str, str] | None = None) -> list[str]:
    if feed_index is None:
        feed_index = _load_feed_index()
    failures: list[str] = []
    for url, label in extract_links(main_html):
        norm = _normalize(url)
        if norm in feed_index:
            continue
        status = _head_status(url)
        if status == 200:
            continue
        if status == 403 and any(d in url for d in PAYWALL_DOMAINS):
            if norm in feed_index:
                continue
            match = _best_feed_match(label, feed_index)
            if match and match[2] >= 0.45:
                continue
            # Paywalled but URL shape matches known feed publisher paths.
            if re.search(r"bloomberg\.com/news/(articles|videos|live-blog)/", url):
                continue
        hint = ""
        match = _best_feed_match(label, feed_index)
        if match and match[2] >= 0.35:
            hint = f" (feed match {match[2]:.2f}: {match[0]})"
        failures.append(f"{status or 'ERR'} {url}\n    {label}{hint}")
    return failures


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "index.html"
    html = path.read_text()
    main_m = re.search(r"<main>[\s\S]*?</main>", html, re.DOTALL)
    if not main_m:
        print("FAIL: no <main> block")
        return 1

    links = extract_links(main_m.group(0))
    print(f"Checking {len(links)} source links in {path}...")
    feed_index = _load_feed_index()
    print(f"Loaded {len(feed_index)} URLs from RSS feeds")

    failures = validate_main(main_m.group(0), feed_index)
    if failures:
        print(f"\nFAIL: {len(failures)} broken or unverified link(s):")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"PASS: all {len(links)} source links verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
