#!/usr/bin/env python3
"""Generate the daily market digest <main> block via the Claude API.

Runs in GitHub Actions on the weekday cron (no local machine involved).
Fetches the RSS/Atom feeds, then asks Claude to rewrite the current <main>
in docs/index.html with today's content, preserving the exact HTML
structure the static template's JS depends on. Writes the result to
incoming/new-main.html for publish_digest.py to consume in the same run.

Requires ANTHROPIC_API_KEY in the environment.
"""
import os
import re
import sys
import time
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


def is_transient_generation_error(e: BaseException) -> bool:
    """Worth a retry: transport drops and retryable API statuses.

    A broken stream surfaces as a RAW httpx error (the SDK retries request
    setup, never a stream that dies mid-read — 10/20 outage: RemoteProtocolError
    ~7 min into generation). The SDK vendors httpx under its own name
    (seen as `httpx2`), so match the exception's module, not an import.
    Billing/4xx stay fatal so the credits case still fails fast and loud.
    """
    mod = type(e).__module__ or ""
    if mod.startswith("httpx") or mod.startswith("httpcore"):
        return True
    if isinstance(e, anthropic.APIConnectionError):
        return True
    if isinstance(e, anthropic.APIStatusError):
        return e.status_code in (408, 409, 429) or e.status_code >= 500
    return False


def generate_message(client, user_content: str, attempts: int = 3, backoff: float = 20.0):
    """Run the digest generation stream, retrying transient failures.

    Retrying the whole stream is safe: nothing is written to disk until the
    final message passes validation in main().
    """
    for attempt in range(1, attempts + 1):
        try:
            with client.messages.stream(
                model="claude-opus-4-8",
                max_tokens=64000,
                thinking={"type": "adaptive"},
                system=SYSTEM,
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                return stream.get_final_message()
        except Exception as e:  # noqa: BLE001 — classified below
            if not is_transient_generation_error(e) or attempt == attempts:
                raise
            wait = backoff * attempt
            print(
                f"generation attempt {attempt}/{attempts} failed "
                f"({type(e).__name__}: {e}); retrying in {wait:.0f}s",
                flush=True,
            )
            time.sleep(wait)


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
    message = generate_message(client, user_content)

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


def _record_failure(reason: str) -> None:
    """Leave the failure cause where the workflow's flag step can read it.

    The publish workflow posts /tmp/digest-failure-reason.txt to the
    maintenance board on job failure, so the board names the cause (e.g.
    "Anthropic API credits exhausted") instead of a bare "run failed".
    """
    reason = " ".join(reason.split())[:1000]
    try:
        Path(os.environ.get("DIGEST_FAILURE_REASON_FILE", "/tmp/digest-failure-reason.txt")).write_text(reason)
    except OSError:
        pass
    print(f"::error::Digest generation failed: {reason}", file=sys.stderr)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if isinstance(e.code, str):
            _record_failure(e.code)
        elif e.code not in (0, None):
            _record_failure(f"generate_digest.py exited {e.code}")
        raise
    except anthropic.APIStatusError as e:
        reason = f"Claude API {e.status_code}: {getattr(e, 'message', e)}"
        if "credit balance is too low" in str(e):
            reason = (
                "Anthropic API credits exhausted — the ANTHROPIC_API_KEY account needs a "
                "top-up at console.anthropic.com -> Plans & Billing before any digest can "
                f"generate. (API said: {getattr(e, 'message', e)})"
            )
        _record_failure(reason)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 — last-resort cause reporting
        _record_failure(f"{type(e).__name__}: {e}")
        raise
