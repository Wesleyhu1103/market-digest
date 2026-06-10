#!/usr/bin/env python3
"""Generate the daily market digest <main> block via the Claude API.

Runs in GitHub Actions on the weekday cron (no local machine involved).
Fetches the RSS feeds, then asks Claude to rewrite the current <main>
in docs/index.html with today's content, preserving the exact HTML
structure the static template's JS depends on. Writes the result to
incoming/new-main.html for publish_digest.py to consume in the same run.

Requires ANTHROPIC_API_KEY in the environment.
"""
import html
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import anthropic

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
OUT = ROOT / "incoming" / "new-main.html"

FEEDS = {
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    "Bloomberg Technology": "https://feeds.bloomberg.com/technology/news.rss",
    "Bloomberg Economics": "https://feeds.bloomberg.com/economics/news.rss",
    "CNBC Top News": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "Calculated Risk": "https://feeds.feedburner.com/calculatedrisk",
    "Stratechery": "https://stratechery.com/feed/",
}
MAX_ITEMS_PER_FEED = 25
MIN_TOTAL_ITEMS = 15
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

SYSTEM = """You are generating Wesley's daily market digest for wesleyhu1103.github.io/market-digest.

Wesley is an intermediate-knowledge market reader on US East Coast time who reads this at 8-9am. He wants granularity: named stories, explicit drivers with directional impact, named bull/bear proponents (specific funds, analysts). No em-dashes. Always contractions. No AI-tell phrases ("genuinely", "honestly", "straightforward", "delve").

You will receive (1) today's date, (2) the current <main> block as a STRUCTURAL TEMPLATE, and (3) today's source material from RSS feeds.

Produce ONLY a complete <main>...</main> block. No markdown fences, no commentary before or after.

STRUCTURAL RULES (the static template's JS breaks if these drift):
- Preserve the template's structure exactly: same sections in the same order, same class names, same ids, same data-attribute patterns. Replace only the content.
- <header class="head">: h1 must be the full weekday date, e.g. "Wednesday, June 10, 2026".
- Three .narrative divs with data-nar="bonds", "iran", "aicapex" (map: rates/bonds -> bonds, geopolitical/oil -> iran, AI/tech -> aicapex). Each has the toggles block with <button class="bull on" data-side="bull">, bear, both buttons, and <div class="bullbear show-bull"> containing .bull and .bear cases with named proponents.
- Verdict section: three .narrative-stack divs (data-narrative="bonds", "iran-oil", "ai-capex"), 5 stack cells each (15 total), ALL <div class="stack-cell pending"> with cell-val "pending" on morning publish, verdict lines "Verdict: Pending".
- Quiz: 3 questions, each <div class="q" data-correct="X"> with 4 <span class="opt" data-opt="A|B|C|D"> options (data-opt, NEVER data-val) and a .feedback div.
- chartData: exactly one <script type="application/json" id="chartData"> as the LAST element before </main>, containing only techMovers, redditSentiment, dealSizes (labels/values/colors arrays matching today's content). NO treasury/brent/credit data (loads from fred-data.json).
- Keep every canvas inside its explicit-height wrapper div exactly as in the template.
- Feedback section: keep ids fb-missing, fb-open, fb-success, verdictFb, vfSaved exactly as in the template.
- Do NOT include <section id="archive"> anywhere.
- Escape apostrophes safely; never break inline JS or JSON.

CONTENT (synthesized from the sources):
- 3 dominant narratives with named bull/bear proponents
- 5-7 US equities stories with tickers and directional drivers
- 5-7 tech/growth stories with metrics
- 5-7 macro/rates stories with explicit drivers
- 4-6 crypto stories
- Major deals and capital markets events
- Reddit sentiment by subreddit: estimate from the day's headlines and label it as estimated in the sources section
- One Learning Opportunity (400-500 words, mechanism-based, no bullets)
- On Deck: next 5 trading days of catalysts
- Sources section: list which feeds contributed and note Reddit is estimated and Gmail newsletters unavailable in automated runs"""


def fetch_feed(name: str, url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    root = ElementTree.fromstring(raw)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = (item.findtext("description") or "").strip()
        date = (item.findtext("pubDate") or "").strip()
        desc = html.unescape(re.sub(r"<[^>]+>", " ", desc))
        desc = re.sub(r"\s+", " ", desc).strip()[:600]
        if title:
            items.append({"title": html.unescape(title), "desc": desc, "date": date})
        if len(items) >= MAX_ITEMS_PER_FEED:
            break
    return items


def gather_sources() -> tuple[str, int]:
    blocks, total = [], 0
    for name, url in FEEDS.items():
        try:
            items = fetch_feed(name, url)
        except Exception as e:
            blocks.append(f"## {name}\n(FAILED: {e})")
            continue
        total += len(items)
        lines = [f"- [{it['date']}] {it['title']}\n  {it['desc']}" for it in items]
        blocks.append(f"## {name}\n" + "\n".join(lines))
    return "\n\n".join(blocks), total


def main() -> int:
    sources_text, total = gather_sources()
    print(f"Fetched {total} items across {len(FEEDS)} feeds")
    if total < MIN_TOTAL_ITEMS:
        raise SystemExit(f"ABORT: only {total} feed items (need {MIN_TOTAL_ITEMS}); not generating a thin digest")

    template = re.search(r"<main>[\s\S]*?</main>", INDEX.read_text())
    if not template:
        raise SystemExit("ABORT: no <main> in docs/index.html")

    today = datetime.now(ZoneInfo("America/New_York"))
    user_content = (
        f"Today's date: {today.strftime('%A, %B %-d, %Y')} ({today.strftime('%Y-%m-%d')})\n\n"
        f"=== STRUCTURAL TEMPLATE (yesterday's <main>; preserve structure, replace content) ===\n"
        f"{template.group(0)}\n\n"
        f"=== TODAY'S SOURCE MATERIAL ===\n{sources_text}"
    )

    client = anthropic.Anthropic()
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=64000,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        message = stream.get_final_message()

    text = next((b.text for b in message.content if b.type == "text"), "")
    print(f"stop_reason={message.stop_reason}, output_tokens={message.usage.output_tokens}")
    if message.stop_reason != "end_turn":
        raise SystemExit(f"ABORT: generation stopped early ({message.stop_reason})")

    m = re.search(r"<main>[\s\S]*</main>", text)
    if not m:
        raise SystemExit("ABORT: no <main> block in model output")
    new_main = m.group(0)
    if 'id="chartData"' not in new_main:
        raise SystemExit("ABORT: generated <main> missing chartData block")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(new_main)
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(new_main) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
