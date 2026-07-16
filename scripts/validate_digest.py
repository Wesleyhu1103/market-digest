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
DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"

STATIC_RULES = validate_static_rules()
RULES = validate_main_rules()
HTML_ONLY = validate_html_only_descs()


def _is_remote_ref(ref: str) -> bool:
    return ref.startswith(("http://", "https://", "//", "data:"))


def _local_asset_path(ref: str, html_path: Path) -> Path:
    clean = ref.split("?", 1)[0].split("#", 1)[0]
    if clean.startswith("/"):
        return (DOCS_ROOT / clean.lstrip("/")).resolve()
    return (html_path.parent / clean).resolve()


def local_asset_refs(html: str) -> list[str]:
    refs: list[str] = []
    refs.extend(re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I))
    refs.extend(re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', html, re.I))
    return [ref for ref in refs if not _is_remote_ref(ref)]


def validate_local_assets(html: str, html_path: Optional[Path]) -> bool:
    if not html_path:
        return True

    refs = local_asset_refs(html)
    missing = [ref for ref in refs if not _local_asset_path(ref, html_path).is_file()]
    if missing:
        print("FAIL local assets: missing " + ", ".join(missing))
        return False
    print(f"OK   local assets: {len(refs)} checked")
    return True


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def collect_js(html: str, html_path: Optional[Path]) -> str:
    """Inline scripts plus local/remote app scripts referenced from index.html."""
    parts: list[str] = []
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
        src = m.group(1).split("?")[0]
        if src.startswith(("http://", "https://", "//")):
            continue
        rel = src.lstrip("/")
        if html_path:
            fp = _local_asset_path(src, html_path)
            if fp.is_file():
                parts.append(fp.read_text())
                continue
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
    if not validate_local_assets(html, html_path):
        failures += 1
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

    total = len(STATIC_RULES) + len(RULES) + 2
    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {total - failures}/{total} checks")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
