#!/usr/bin/env python3
"""Generate docs/js/site-config.js from docs/site-config.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "site-config.json"
OUT = ROOT / "docs" / "js" / "site-config.js"


def main() -> None:
    cfg = json.loads(SRC.read_text())
    body = json.dumps(cfg, indent=2)
    OUT.write_text(
        "// Auto-generated from docs/site-config.json — run: python3 scripts/sync_site_config.py\n"
        f"window.SiteConfig = {body};\n"
        "var MD_VERCEL_ORIGIN = SiteConfig.vercelOrigin;\n"
        "var MD_ASSET_VERSION = SiteConfig.assetVersion;\n"
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
