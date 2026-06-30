#!/usr/bin/env python3
"""Generate the daily market digest <main> block via the Claude API.

Runs in GitHub Actions on the weekday cron (no local machine involved).
Fetches the RSS/Atom feeds, then asks Claude to rewrite the current <main>
in docs/index.html with today's content, preserving the exact HTML
structure the static template's JS depends on. Writes the result to
incoming/new-main.html for publish_digest.py to consume in the same run.

Requires ANTHROPIC_API_KEY in the environment.
"""
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
OUT = ROOT / "incoming" / "new-main.html"
REPORT = ROOT / "incoming" / "feed-report.json"

sys.path.insert(0, str(ROOT / "scripts"))
from feed_sources import (  # noqa: E402
    MIN_TOTAL_FRESH_ITEMS,
    build_feed_report_json,
    build_sources_html,
    gather_sources,
    inject_sources_section,
)

SYSTEM = """You are generating Wesley's daily market digest for wesleyhu1103.github.io/market-digest.

Wesley is an intermediate-knowledge market reader on US East Coast time who reads this at 8-9am. He wants granularity: named stories, explicit drivers with directional impact, named bull/bear proponents (specific funds, analysts). No em-dashes. Always contractions. No AI-tell phrases ("genuinely", "honestly", "straightforward", "delve").

You will receive (1) today's date, (2) the current <main> block as a STRUCTURAL TEMPLATE, (3) today's source material from RSS/Atom feeds, and (4) a machine-generated FEED_REPORT JSON.

Produce ONLY a complete <main>...</main> block. No markdown fences, no commentary before or after.

STRUCTURAL RULES (the static template's JS breaks if these drift):
- Preserve the template's structure exactly: same sections in the same order, same class names, same ids, same data-attribute patterns. Replace only the content.
- <header class="head">: h1 must be the full weekday date, e.g. "Wednesday, June 10, 2026". The `.meta` lede is exactly 2-3 short sentences: today's structural context (e.g. quarter-end, jobs day, FOMC) plus one or two secondary threads. Do NOT restate or preview framingData's storyTitle; that headline lives in the 5 Desks widget immediately below.
- Three .narrative divs with data-nar="bonds", "iran", "aicapex" (map: rates/bonds -> bonds, geopolitical/oil -> iran, AI/tech -> aicapex). Each has the toggles block with <button class="bull on" data-side="bull">, bear, both buttons, and <div class="bullbear show-bull"> containing .bull and .bear cases with named proponents.
- Verdict section: three .narrative-stack divs (data-narrative="bonds", "iran-oil", "ai-capex"), 5 stack cells each (15 total), ALL <div class="stack-cell pending"> with cell-val "pending" on morning publish, verdict lines "Verdict: Pending".
- Quiz: 3 questions, each <div class="q" data-correct="X"> with 4 <span class="opt" data-opt="A|B|C|D"> options (data-opt, NEVER data-val) and a .feedback div. The correct answer must NOT be the longest option: keep all 4 options within a similar length band (roughly the same number of words), so length is not a tell. Make distractors plausible and specifically wrong (a real misconception, a swapped cause/effect, a true-but-irrelevant fact), not obvious throwaways. Vary the correct data-opt across the 3 questions and across days; do not default to the verbose option or to a fixed position.
- chartData: exactly one <script type="application/json" id="chartData"> as the LAST element before </main>, containing only techMovers, redditSentiment, dealSizes (labels/values/colors arrays matching today's content). NO treasury/brent/credit data (loads from fred-data.json).
- framingData (optional but preferred): a <script type="application/json" id="framingData"> placed inside <section id="framing"> as its last child (before </section>). JSON shape: {"storyTitle": "<one shared story everyone covered today>", "framings": [{"outlet": "WSJ", "headline": "<that outlet's actual headline angle>", "angle": "<one sentence on how they frame it>", "lean": <integer -100 bearish..100 bullish>, "pull": "<a short representative pull-quote>"}, ...]} with 3-5 outlets drawn from WSJ, The Economist, NYT, CNBC, Bloomberg, Financial Times, The Atlantic. The static template's "Framing Compare" widget reads this; if absent it falls back to a default. Keep it valid JSON with escaped apostrophes; do NOT break inline JSON.
- Story items in #equities, #tech, #macro, #crypto, #buyside, and #deals use condensed <details class="deal"> dropdowns (NOT <ul><li>). Pattern: <details class="deal"><summary><strong>headline</strong></summary><div class="deal-body">...</div></details>. Equities/tech/macro/crypto/buyside: one <p> with the driver/context, then <p class="deal-source"><a href="..." target="_blank" rel="noopener noreferrer">Source: Outlet -- Headline</a></p> using a real URL from today's feeds when available. Deals: Why / Outlook / What it means paragraphs, then the same deal-source line. Learning Opportunity and details.dive blocks also end with deal-source link(s). After the buyside analyst dropdowns, include one `.buyside-summary` block with the same Bull/Bear/Both toggles and `.bullbear show-bull` structure as `.narrative` (NOT `.buyside-grid` cards).
- Keep every canvas inside its explicit-height wrapper div exactly as in the template.
- Feedback section: keep ids fb-missing, fb-open, fb-success, verdictFb, vfSaved exactly as in the template.
- Do NOT include <section id="archive"> anywhere.
- Escape apostrophes safely; never break inline JS or JSON.
- Include <section id="sources"> as a placeholder; it will be replaced automatically after generation. Do not invent feed status prose.

CONTENT (synthesized from the sources):
- 3 dominant narratives with named bull/bear proponents
- 5-7 US equities stories with tickers and directional drivers
- 5-7 tech/growth stories with metrics
- 5-7 macro/rates stories with explicit drivers
- 4-6 crypto stories (use CoinDesk items when present)
- Major deals and capital markets events
- Reddit sentiment by subreddit: estimate from the day's headlines
- One Learning Opportunity (400-500 words, mechanism-based, no bullets)
- On Deck: next 5 trading days of catalysts"""


def main() -> int:
    sources_text, reports, total_fresh = gather_sources()
    ok_feeds = sum(1 for r in reports if r.status == "ok")
    print(f"Fetched {total_fresh} fresh items from {ok_feeds}/{len(reports)} feeds")
    for r in reports:
        print(f"  {r.name}: {r.status} ({r.items_fresh}/{r.items_fetched} fresh)")

    if total_fresh < MIN_TOTAL_FRESH_ITEMS:
        raise SystemExit(
            f"ABORT: only {total_fresh} fresh feed items in last 36h "
            f"(need {MIN_TOTAL_FRESH_ITEMS}); not generating a thin digest"
        )

    template = re.search(r"<main>[\s\S]*?</main>", INDEX.read_text())
    if not template:
        raise SystemExit("ABORT: no <main> in docs/index.html")

    today = datetime.now(ZoneInfo("America/New_York"))
    feed_report = build_feed_report_json(reports)
    user_content = (
        f"Today's date: {today.strftime('%A, %B %-d, %Y')} ({today.strftime('%Y-%m-%d')})\n\n"
        f"=== STRUCTURAL TEMPLATE (yesterday's <main>; preserve structure, replace content) ===\n"
        f"{template.group(0)}\n\n"
        f"=== FEED_REPORT (authoritative feed status; do not contradict) ===\n"
        f"{feed_report}\n\n"
        f"=== TODAY'S SOURCE MATERIAL (items from last 36 hours) ===\n"
        f"{sources_text}"
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
    new_main = inject_sources_section(m.group(0), build_sources_html(reports, today))
    if 'id="chartData"' not in new_main:
        raise SystemExit("ABORT: generated <main> missing chartData block")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(new_main)
    REPORT.write_text(feed_report)
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(new_main) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
