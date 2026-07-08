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
from digest_contracts import build_system_prompt  # noqa: E402
from feed_sources import (  # noqa: E402
    MIN_TOTAL_FRESH_ITEMS,
    build_feed_report_json,
    build_sources_html,
    gather_sources,
    inject_sources_section,
)

SYSTEM = build_system_prompt()


def fetch_community_votes_block() -> str:
    """Top approved proposals for On Deck prompt (empty if DB unavailable)."""
    db_cli = ROOT / "scripts" / "feedback_db.mjs"
    if not db_cli.exists():
        return ""
    import json
    import subprocess

    try:
        proc = subprocess.run(
            ["node", str(db_cli), "top-voted", "10"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=30,
        )
        if proc.returncode != 0:
            return ""
        rows = json.loads(proc.stdout or "[]")
        if not rows:
            return ""
        lines = []
        for r in rows:
            title = (r.get("title") or "").strip()
            cat = r.get("category") or "features"
            votes = r.get("vote_count") or 0
            if title:
                lines.append(f"[{cat}] {title} ({votes} votes)")
        if not lines:
            return ""
        return (
            "=== COMMUNITY_VOTES (top reader-requested changes; consider for On Deck Reader requests) ===\n"
            + "\n".join(lines)
            + "\n\n"
        )
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return ""


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
    community_votes = fetch_community_votes_block()
    user_content = (
        f"Today's date: {today.strftime('%A, %B %-d, %Y')} ({today.strftime('%Y-%m-%d')})\n\n"
        f"=== STRUCTURAL TEMPLATE (yesterday's <main>; preserve structure, replace content) ===\n"
        f"{template.group(0)}\n\n"
        f"=== FEED_REPORT (authoritative feed status; do not contradict) ===\n"
        f"{feed_report}\n\n"
        f"{community_votes}"
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
