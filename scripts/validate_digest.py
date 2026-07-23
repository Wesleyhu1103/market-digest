#!/usr/bin/env python3
"""Structural + JS parse checks for market-digest index.html."""
import re
import subprocess
import sys
import tempfile
import os
import urllib.request
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from digest_contracts import (  # noqa: E402
    validate_html_only_descs,
    validate_main_rules,
    validate_static_rules,
)

LIVE_URL = "https://raw.githubusercontent.com/wesleyhu1103/market-digest/main/docs/index.html"
LIVE_BASE = "https://raw.githubusercontent.com/wesleyhu1103/market-digest/main/docs/"

STATIC_RULES = validate_static_rules()
RULES = validate_main_rules()
HTML_ONLY = validate_html_only_descs()


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def _is_remote_asset(ref: str) -> bool:
    return ref.startswith(("http://", "https://", "//", "data:"))


def validate_local_assets(html: str, html_path: Optional[Path]) -> list[str]:
    """Return missing local script/style refs, resolved like a browser would."""
    if not html_path:
        return []
    missing: list[str] = []
    asset_patterns = (
        r'<script[^>]+src=["\']([^"\']+)["\']',
        r'<link(?=[^>]+\brel=["\']stylesheet["\'])(?=[^>]+\bhref=["\']([^"\']+)["\'])[^>]*>',
    )
    for pat in asset_patterns:
        for m in re.finditer(pat, html, re.I):
            ref = m.group(1).split("?")[0]
            if _is_remote_asset(ref):
                continue
            fp = (html_path.parent / ref.lstrip("/")).resolve()
            if not fp.is_file():
                missing.append(ref)
    return missing


def collect_js(html: str, html_path: Optional[Path]) -> str:
    """Inline scripts plus local/remote app scripts referenced from index.html."""
    parts: list[str] = []
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
        src = m.group(1).split("?")[0]
        if _is_remote_asset(src):
            continue
        rel = src.lstrip("/")
        if html_path:
            fp = (html_path.parent / rel).resolve()
            if fp.is_file():
                parts.append(fp.read_text())
            else:
                print(f"WARN: missing local script {src}")
            continue
        try:
            parts.append(_fetch_text(LIVE_BASE + rel))
        except OSError:
            print(f"WARN: could not load script {src}")
    for block in re.findall(r"<script>([\s\S]*?)</script>", html):
        parts.append(block)
    return "\n\n".join(parts)


def check_js(js_body: str) -> bool:
    if not js_body.strip():
        print("FAIL JS: no script content")
        return False
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js_body)
        tmp = f.name
    r = subprocess.run(
        ["node", "-e", f"try{{new Function(require('fs').readFileSync('{tmp}','utf8'));process.exit(0)}}catch(e){{console.error(e.message);process.exit(1)}}"],
        capture_output=True,
        text=True,
    )
    os.unlink(tmp)
    ok = r.returncode == 0
    print(("OK   " if ok else "FAIL ") + "JS parse: " + (r.stderr.strip() or "OK"))
    return ok


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    html_path = Path(path).resolve() if path else None
    if path:
        html = Path(path).read_text()
    else:
        html = _fetch_text(LIVE_URL)

    js_bundle = collect_js(html, html_path)

    main_block = re.search(r"<main>[\s\S]*?</main>", html, re.DOTALL)
    if not main_block:
        print("FAIL: no <main> block")
        sys.exit(1)
    main_block = main_block.group(0)

    failures = 0
    missing_assets = validate_local_assets(html, html_path)
    if missing_assets:
        for ref in missing_assets:
            print(f"FAIL local asset exists: {ref}")
        failures += len(missing_assets)
    for desc, pat, exp, scope_kind in STATIC_RULES:
        scope = js_bundle if scope_kind == "js" else html
        n = len(re.findall(pat, scope, re.DOTALL | re.I))
        ok = n == exp
        print(("OK   " if ok else "FAIL ") + f"{desc}: {n}/{exp}")
        if not ok:
            failures += 1
    for desc, pat, exp in RULES:
        scope = html if desc in HTML_ONLY else main_block
        n = len(re.findall(pat, scope, re.DOTALL | re.I))
        ok = n == exp
        print(("OK   " if ok else "FAIL ") + f"{desc}: {n}/{exp}")
        if not ok:
            failures += 1

    if not check_js(js_bundle):
        failures += 1

    total = len(STATIC_RULES) + len(RULES) + 1 + len(missing_assets)
    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {total - failures}/{total} checks")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
