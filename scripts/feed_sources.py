#!/usr/bin/env python3
"""Fetch and filter RSS/Atom feeds for the daily digest pipeline."""
from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

FEEDS: dict[str, str] = {
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    "Bloomberg Technology": "https://feeds.bloomberg.com/technology/news.rss",
    "Bloomberg Economics": "https://feeds.bloomberg.com/economics/news.rss",
    "CNBC Top News": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    # Non-Bloomberg general-market feeds: CNBC Top News alone delivered only
    # 1-9 fresh items/day vs Bloomberg's 45-75, so the digest skewed Bloomberg
    # by pool composition. Verify additions with .github/workflows/feed-check.yml.
    "CNBC Finance": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "CNBC Economy": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "MarketWatch Top Stories": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "WSJ Markets": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "FT Home": "https://www.ft.com/rss/home",
    "Matt Levine Money Stuff": "https://www.bloomberg.com/opinion/authors/ARbTQlRLRjE/matthew-s-levine.rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss",
    "Stratechery": "https://stratechery.com/feed/",
}

MAX_ITEMS_PER_FEED = 25
FRESH_HOURS = 36
MIN_TOTAL_FRESH_ITEMS = 12
FETCH_RETRIES = 2


@dataclass
class FeedItem:
    title: str
    url: str
    desc: str
    published: datetime | None
    published_label: str


@dataclass
class FeedResult:
    name: str
    url: str
    status: str
    items_fetched: int = 0
    items_fresh: int = 0
    newest: str | None = None
    error: str | None = None


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        if "T" in raw and ("+" in raw or raw.endswith("Z")):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None


def _strip_html(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _text_el(parent: ElementTree.Element, *paths: str) -> str:
    for path in paths:
        if path.startswith("a:"):
            el = parent.find(path, ATOM_NS)
        else:
            el = parent.find(path)
        if el is not None and (el.text or "").strip():
            return el.text.strip()
        if el is not None and el.get("href"):
            return el.get("href", "").strip()
    return ""


def _fetch_bytes(url: str) -> bytes:
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    last_err: Exception | None = None
    for attempt in range(FETCH_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"},
            )
            return opener.open(req, timeout=30).read()
        except (OSError, TimeoutError, urllib.error.URLError) as e:
            last_err = e
            if attempt < FETCH_RETRIES:
                time.sleep(2 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def _parse_items(raw: bytes) -> list[FeedItem]:
    root = ElementTree.fromstring(raw)
    tag = _local_tag(root.tag).lower()
    items: list[FeedItem] = []

    if tag == "feed":
        nodes = root.findall("a:entry", ATOM_NS)
        for entry in nodes:
            title = _text_el(entry, "a:title")
            link_el = entry.find("a:link", ATOM_NS)
            link = (link_el.get("href", "") if link_el is not None else "").strip()
            desc = _strip_html(
                _text_el(entry, "a:summary", "a:content") or ""
            )[:600]
            pub_raw = _text_el(entry, "a:published", "a:updated")
            pub = _parse_datetime(pub_raw)
            if title:
                items.append(
                    FeedItem(
                        title=html.unescape(title),
                        url=link,
                        desc=desc,
                        published=pub,
                        published_label=pub_raw or "",
                    )
                )
    else:
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = _strip_html(item.findtext("description") or "")[:600]
            pub_raw = (item.findtext("pubDate") or item.findtext("date") or "").strip()
            pub = _parse_datetime(pub_raw)
            if title:
                items.append(
                    FeedItem(
                        title=html.unescape(title),
                        url=link,
                        desc=desc,
                        published=pub,
                        published_label=pub_raw or "",
                    )
                )

    return items[:MAX_ITEMS_PER_FEED]


def _fresh_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=FRESH_HOURS)


def _is_fresh(item: FeedItem, cutoff: datetime) -> bool:
    if item.published is None:
        return True
    pub = item.published
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    return pub >= cutoff


def fetch_feed(name: str, url: str) -> tuple[list[FeedItem], FeedResult]:
    try:
        raw_items = _parse_items(_fetch_bytes(url))
    except Exception as e:
        return [], FeedResult(name=name, url=url, status="failed", error=str(e))

    cutoff = _fresh_cutoff()
    fresh = [it for it in raw_items if _is_fresh(it, cutoff)]
    newest = None
    dated = [it for it in fresh if it.published is not None]
    if dated:
        newest_dt = max(
            (it.published.replace(tzinfo=timezone.utc) if it.published.tzinfo is None else it.published.astimezone(timezone.utc))
            for it in dated
        )
        newest = newest_dt.astimezone(ET).strftime("%Y-%m-%d %H:%M ET")

    status = "ok" if fresh else ("stale" if raw_items else "empty")
    return fresh, FeedResult(
        name=name,
        url=url,
        status=status,
        items_fetched=len(raw_items),
        items_fresh=len(fresh),
        newest=newest,
    )


def build_feed_url_index() -> dict[str, str]:
    """Map normalized article URLs to titles from all configured feeds (no freshness filter)."""
    index: dict[str, str] = {}
    for name, url in FEEDS.items():
        try:
            items = _parse_items(_fetch_bytes(url))
        except Exception:
            continue
        for it in items:
            if it.url:
                index[_normalize_url(it.url)] = it.title
    return index


def _normalize_url(url: str) -> str:
    return url.rstrip("/").split("#", 1)[0]


def gather_sources() -> tuple[str, list[FeedResult], int]:
    blocks: list[str] = []
    reports: list[FeedResult] = []
    total_fresh = 0

    for name, url in FEEDS.items():
        items, report = fetch_feed(name, url)
        reports.append(report)
        total_fresh += len(items)
        if report.status == "failed":
            blocks.append(f"## {name}\n(FAILED: {report.error})")
            continue
        if not items:
            blocks.append(f"## {name}\n(no items in last {FRESH_HOURS}h; fetched {report.items_fetched} older)")
            continue
        lines = [
            f"- [{it.published_label or 'undated'}] {it.title}\n  URL: {it.url}\n  {it.desc}"
            for it in items if it.url
        ] or [
            f"- [{it.published_label or 'undated'}] {it.title}\n  {it.desc}"
            for it in items
        ]
        blocks.append(f"## {name}\n" + "\n".join(lines))

    return "\n\n".join(blocks), reports, total_fresh


def build_feed_report_json(reports: list[FeedResult]) -> str:
    payload = {
        "generated_at": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
        "fresh_window_hours": FRESH_HOURS,
        "feeds": [asdict(r) for r in reports],
        "notes": {
            "reddit": "estimated from headlines (no API in automated runs)",
            "gmail": "unavailable in automated runs",
            "fred": "loaded from docs/fred-data.json at page render",
        },
    }
    return json.dumps(payload, indent=2)


def build_sources_html(reports: list[FeedResult], today: datetime) -> str:
    worked = [
        f"{r.name} ({r.items_fresh} fresh"
        + (f", newest {r.newest}" if r.newest else "")
        + ")"
        for r in reports
        if r.status == "ok"
    ]
    stale = [
        f"{r.name} ({r.items_fetched} fetched, 0 in last {FRESH_HOURS}h"
        + (f", newest {r.newest}" if r.newest else "")
        + ")"
        for r in reports
        if r.status == "stale"
    ]
    failed = [f"{r.name}: {r.error}" for r in reports if r.status == "failed"]
    empty = [r.name for r in reports if r.status == "empty"]

    failed_bits = []
    if failed:
        failed_bits.append("Failed feeds: " + "; ".join(failed))
    if stale:
        failed_bits.append("Stale feeds (no items in window): " + "; ".join(stale))
    if empty:
        failed_bits.append("Empty feeds: " + ", ".join(empty))
    failed_bits.append(
        "Reddit sentiment is estimated from headlines (no Reddit API in automated runs)."
    )
    failed_bits.append(
        "Gmail newsletters unavailable in automated runs (WSJ/NYT/Morning Brew not pulled)."
    )

    date_label = today.strftime("%a %b %-d, %Y")
    worked_text = "; ".join(worked) if worked else "None"
    failed_text = " ".join(failed_bits)

    return f"""  <section id="sources">
    <div class="source-note">
      <h4>Sources &amp; Data Notes ({date_label})</h4>
      <p><strong>Worked:</strong> {html.escape(worked_text)}</p>
      <p><strong>Failed / Blocked:</strong> {html.escape(failed_text)}</p>
    </div>
  </section>"""


def check_feeds() -> int:
    """CLI: fetch every configured feed and print a status table.

    Exit code is 0 unless EVERY feed fails (stale/empty feeds are normal —
    e.g. Money Stuff on days with no column). Used by feed-check.yml.
    """
    failed = 0
    print(f"{'feed':30s} {'status':8s} {'fetched':>7s} {'fresh':>5s}  newest")
    for name, url in FEEDS.items():
        _, rep = fetch_feed(name, url)
        if rep.status == "failed":
            failed += 1
        detail = rep.error if rep.status == "failed" else (rep.newest or "-")
        print(f"{name:30s} {rep.status:8s} {rep.items_fetched:7d} {rep.items_fresh:5d}  {detail}")
    print(f"\n{len(FEEDS) - failed}/{len(FEEDS)} feeds reachable")
    return 1 if failed == len(FEEDS) else 0


def inject_sources_section(main_html: str, sources_html: str) -> str:
    if re.search(r'<section id=["\']sources["\']', main_html):
        return re.sub(
            r'<section id=["\']sources["\']>[\s\S]*?</section>',
            sources_html.strip(),
            main_html,
            count=1,
        )
    return main_html.replace("</main>", sources_html + "\n</main>", 1)


if __name__ == "__main__":
    raise SystemExit(check_feeds())
