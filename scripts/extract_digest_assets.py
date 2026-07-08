#!/usr/bin/env python3
"""One-shot helper: extract CSS/JS from docs/index.html into docs/css/ and docs/js/."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
ASSET_V = "20260708"

# (filename, start_line, end_line) — 1-based, inclusive, from original index.html
BODY_SPLITS = [
    ("config.js", 1394, 1441),
    ("repair-dom.js", 1443, 1536),
    ("digest-ui.js", 1538, 1716),
    ("charts-core.js", 1719, 2044),
    ("archive.js", 2046, 2122),
    ("artifact-equities.js", 2124, 2433),
    ("charts-macro.js", 2435, 3047),
    ("artifact-framing.js", 3049, 3128),
    ("verdict-updater.js", 3130, 3462),
    ("digest-init.js", 3465, 3727),
]

SCRIPT_ORDER = [
    "config.js",
    "repair-dom.js",
    "digest-ui.js",
    "charts-core.js",
    "archive.js",
    "artifact-equities.js",
    "charts-macro.js",
    "artifact-framing.js",
    "verdict-updater.js",
    "digest-init.js",
]


def strip_script_indent(lines: list[str]) -> str:
    out = []
    for line in lines:
        if line.startswith("  "):
            out.append(line[2:])
        else:
            out.append(line)
    text = "\n".join(out).rstrip() + "\n"
    return text


def read_lines(path: Path) -> list[str]:
    return path.read_text().splitlines()


def main() -> None:
    lines = read_lines(INDEX)

    # CSS: lines 128-619 inside <style>
    css = "\n".join(line[2:] if line.startswith("  ") else line for line in lines[127:619])
    (ROOT / "docs/css").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/css/digest.css").write_text(css.rstrip() + "\n")

    # MarketFeed in head: lines 13-125
    mf = strip_script_indent(lines[12:125])
    (ROOT / "docs/js").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/js/market-feed.js").write_text(mf)

    for fname, start, end in BODY_SPLITS:
        chunk = strip_script_indent(lines[start - 1 : end])
        (ROOT / "docs/js" / fname).write_text(chunk)

    # Rebuild index: head (1-11), assets, body from 621-1390, scripts, close
    head = "\n".join(lines[0:11])
    body = "\n".join(lines[621:1389])  # <body> … timeline drawer (before app scripts)

    script_tags = "\n".join(
        f'<script src="js/{name}?v={ASSET_V}"></script>' for name in SCRIPT_ORDER
    )

    new_html = f"""{head}
<script src="js/market-feed.js?v={ASSET_V}"></script>
<link rel="stylesheet" href="css/digest.css?v={ASSET_V}">
</head>
{body}

{script_tags}

</body>
</html>
"""
    INDEX.write_text(new_html)
    print("Extracted css/digest.css, js/*.js; rewrote docs/index.html")


if __name__ == "__main__":
    main()
