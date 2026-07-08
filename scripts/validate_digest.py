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

LIVE_URL = "https://raw.githubusercontent.com/wesleyhu1103/market-digest/main/docs/index.html"
LIVE_BASE = "https://raw.githubusercontent.com/wesleyhu1103/market-digest/main/docs/"

# Full-page checks (static template outside <main>) — guard regressions in narrative
# threads date logic and mobile drawer/toggle behavior.
STATIC_RULES = [
    ("narrative editionDayLabel", r"function editionDayLabel\(\)", 1, "js"),
    ("no hardcoded todayLabel", r"todayLabel\s*=\s*['\"][A-Za-z]", 0, "js"),
    ("timeline drawer id", r'id="tlDrawer"', 1, "html"),
    ("timeline drawer not nested", r'<div class="tl-scrim"[^>]*>\s*<div class="tl-drawer"', 0, "html"),
    ("ios scroll lock helper", r"function lockBodyScroll\(\)", 1, "js"),
    ("bull/bear delegated clicks", r"\.closest\(['\"]\.narrative \.toggles button", 1, "js"),
]

RULES = [
    ("3 narrative data-nar", r'<div class="narrative" data-nar="(bonds|iran|aicapex)">', 3),
    ("4 bullbear show-bull", r'<div class="bullbear show-bull">', 4),
    ("bull on (flex order)", r'class="bull on"[^>]*data-side="bull"|data-side="bull"[^>]*class="bull on"', 4),
    ("12 quiz data-opt", r'<span class="opt" data-opt="[a-dA-D]">', 12),
    ("no quiz data-val on opts", r'<span class="opt"[^>]*data-val=', 0),
    ("chartData once", r'id="chartData"', 1),
    ("chartData last in main", r'<script[^>]*id="chartData"[^>]*>[\s\S]*?</script>\s*</main>', 1),
    ("techMovers wrapped", r'height:\d+px[^"]*"><canvas id="techMovers"', 1),
    ("7 chart canvases", r'<canvas id="(techMovers|redditSentiment|treasuryYields|brentChart|creditChart|stressChart|dealSizes)"', 7),
    ("3 narrative-stacks", r'<div class="narrative-stack" data-narrative="(bonds|iran-oil|ai-capex)">', 3),
    ("fb-missing textarea", r'<textarea[^>]*id="fb-missing"', 1),
    ("archive-mount outside main", r'</main>[\s\S]*<div id="archive-mount"', 1),
]


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
            fp = (html_path.parent / rel).resolve()
            if fp.is_file():
                parts.append(fp.read_text())
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
    html_only = {"chartData last in main", "archive-mount outside main"}
    for desc, pat, exp, scope_kind in STATIC_RULES:
        scope = js_bundle if scope_kind == "js" else html
        n = len(re.findall(pat, scope, re.DOTALL | re.I))
        ok = n == exp
        print(("OK   " if ok else "FAIL ") + f"{desc}: {n}/{exp}")
        if not ok:
            failures += 1
    for desc, pat, exp in RULES:
        scope = html if desc in html_only else main_block
        n = len(re.findall(pat, scope, re.DOTALL | re.I))
        ok = n == exp
        print(("OK   " if ok else "FAIL ") + f"{desc}: {n}/{exp}")
        if not ok:
            failures += 1

    if not check_js(js_bundle):
        failures += 1

    total = len(STATIC_RULES) + len(RULES) + 1
    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {total - failures}/{total} checks")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
