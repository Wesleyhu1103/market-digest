#!/usr/bin/env python3
"""Apply a generated <main> block to docs/index.html in the local checkout.

Run by .github/workflows/publish-digest.yml. This replaces the old
PAT-over-Contents-API publish flow: the digest agent only uploads
incoming/new-main.html; this script does the rest with plain file I/O.

Steps:
  1. If no incoming/new-main.html exists, exit 0 (scheduled FRED-only run).
  2. Archive the previous day's index.html and update archive/manifest.json.
  3. Repair the new <main> via repair_main.repair_main_html.
  4. Splice it into docs/index.html and update date strings.
  5. Remove the incoming file so the publish commit cleans it up.

Validation (structure + JS parse) runs separately via validate_digest.py.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
INCOMING = ROOT / "incoming" / "new-main.html"
ARCHIVE_DIR = ROOT / "docs" / "archive"
MANIFEST = ARCHIVE_DIR / "manifest.json"

sys.path.insert(0, str(ROOT / "scripts"))
from repair_main import repair_main_html


def archive_safe_asset_paths(html: str) -> str:
    """Archive pages live one level deeper, so root-local assets need ../ paths."""
    html = re.sub(
        r'(<script\b[^>]*\bsrc=")(js/[^"]*)(")',
        r"\1../\2\3",
        html,
        flags=re.I,
    )
    html = re.sub(
        r'(<link\b[^>]*\brel="stylesheet"[^>]*\bhref=")(css/[^"]*)(")',
        r"\1../\2\3",
        html,
        flags=re.I,
    )
    html = re.sub(
        r'(<link\b[^>]*\bhref=")(css/[^"]*)("[^>]*\brel="stylesheet"[^>]*>)',
        r"\1../\2\3",
        html,
        flags=re.I,
    )
    return html


def archive_previous_day(current_html: str, today_iso: str) -> None:
    old_h1 = re.search(r"<h1>([^<]+)</h1>", current_html)
    if not old_h1:
        return
    try:
        dt = datetime.strptime(old_h1.group(1).strip(), "%A, %B %d, %Y")
    except ValueError:
        return
    old_date_iso = dt.strftime("%Y-%m-%d")
    if old_date_iso == today_iso:
        return

    banner = (
        '<div style="background:var(--accent-soft);border-left:4px solid var(--accent);'
        'padding:14px 22px;margin:0 0 18px;font-size:14px;">'
        f"<strong>Archived — {old_date_iso}</strong> · "
        '<a href="../index.html" style="color:var(--accent);">← back to today</a></div>'
    )
    snapshot_path = ARCHIVE_DIR / f"{old_date_iso}.html"
    if not snapshot_path.exists():
        snapshot = re.sub(r"<main>", lambda m: "<main>\n" + banner, current_html, count=1)
        snapshot = archive_safe_asset_paths(snapshot)
        snapshot_path.write_text(snapshot)
        print(f"Archived {snapshot_path.relative_to(ROOT)}")

    summary = ""
    old_meta = re.search(r'<div class="meta">([\s\S]*?)</div>', current_html)
    if old_meta:
        summary = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", old_meta.group(1))).strip()[:240]
    new_entry = {
        "date": old_date_iso,
        "weekday": dt.strftime("%a"),
        "h1": old_h1.group(1).strip(),
        "summary": summary,
        "url": f"archive/{old_date_iso}.html",
    }
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    manifest = [e for e in manifest if e.get("date") != old_date_iso] + [new_entry]
    manifest.sort(key=lambda e: e["date"])
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest updated ({len(manifest)} entries)")


def main() -> int:
    if not INCOMING.exists():
        print("No incoming/new-main.html — nothing to publish (FRED-only run).")
        return 0

    new_main = INCOMING.read_text()
    if "<main>" not in new_main or "</main>" not in new_main:
        raise SystemExit("ABORT: incoming/new-main.html must contain <main>...</main>")

    current_html = INDEX.read_text()
    today = datetime.now(ZoneInfo("America/New_York")).date()
    today_iso = today.isoformat()

    archive_previous_day(current_html, today_iso)

    main_html = repair_main_html(new_main)
    new_html = re.sub(r"<main>.*?</main>", lambda m: main_html, current_html, count=1, flags=re.DOTALL)

    new_html = re.sub(
        r"Market Digest\s*[—\-]\s*[\w,\s]+\d{4}",
        f'Market Digest — {today.strftime("%a %b %-d, %Y")}',
        new_html,
    )
    new_html = re.sub(r"date:\s*'\d{4}-\d{2}-\d{2}'", f"date: '{today_iso}'", new_html)
    new_html = re.sub(
        r"marketDigest_feedback_\d{4}-\d{2}-\d{2}",
        f"marketDigest_feedback_{today_iso}",
        new_html,
    )

    INDEX.write_text(new_html)
    INCOMING.unlink()
    report = ROOT / "incoming" / "feed-report.json"
    if report.exists():
        report.unlink()
    print(f"Updated docs/index.html for {today_iso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
