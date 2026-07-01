#!/usr/bin/env python3
"""Structural + JS parse checks for market-digest index.html."""
import re
import subprocess
import sys
import tempfile
import os
import urllib.request

LIVE_URL = "https://raw.githubusercontent.com/wesleyhu1103/market-digest/main/docs/index.html"

# Full-page checks (static template outside <main>) — guard regressions in narrative
# threads date logic and mobile drawer/toggle behavior.
STATIC_RULES = [
    ("narrative editionDayLabel", r"function editionDayLabel\(\)", 1),
    ("no hardcoded todayLabel", r"todayLabel\s*=\s*['\"][A-Za-z]", 0),
    ("timeline drawer id", r'id="tlDrawer"', 1),
    ("timeline drawer not nested", r'<div class="tl-scrim"[^>]*>\s*<div class="tl-drawer"', 0),
    ("ios scroll lock helper", r"function lockBodyScroll\(\)", 1),
    ("bull/bear delegated clicks", r"\.closest\(['\"]\.narrative \.toggles button", 1),
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


def check_js(html: str) -> bool:
    scripts = re.findall(r"<script>([\s\S]*?)</script>", html)
    if not scripts:
        print("FAIL JS: no inline script")
        return False
    body = max(scripts, key=len)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(body)
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
    if path:
        html = open(path).read()
    else:
        req = urllib.request.Request(LIVE_URL, headers={"Cache-Control": "no-cache"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

    main_block = re.search(r"<main>[\s\S]*?</main>", html, re.DOTALL)
    if not main_block:
        print("FAIL: no <main> block")
        sys.exit(1)
    main_block = main_block.group(0)

    failures = 0
    html_only = {"chartData last in main", "archive-mount outside main", "JS parse"}
    for desc, pat, exp in STATIC_RULES:
        n = len(re.findall(pat, html, re.DOTALL | re.I))
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

    if not check_js(html):
        failures += 1

    total = len(STATIC_RULES) + len(RULES) + 1
    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {total - failures}/{total} checks")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
