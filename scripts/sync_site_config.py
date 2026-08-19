#!/usr/bin/env python3
"""Generate docs/js/site-config.js and sync asset cache-bust versions.

Single source of truth is docs/site-config.json. Running this:
  1. regenerates docs/js/site-config.js (window.SiteConfig + globals), and
  2. rewrites the ?v=<assetVersion> cache-bust on local js/ and css/ tags in
     docs/index.html, docs/admin.html, and archive snapshots so returning visitors fetch fresh
     assets after any JS/CSS change.

Workflow: edit docs/site-config.json (bump assetVersion when js/css changes),
then run `python3 scripts/sync_site_config.py`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "site-config.json"
OUT = ROOT / "docs" / "js" / "site-config.js"
# Matches a local asset reference (src="js/…" / href="css/…") carrying a
# ?v=<digits> cache-bust. Archive snapshots use ../js/ and ../css/. Leaves
# CDN URLs and font query strings untouched.
ASSET_TAG_RE = re.compile(r'((?:src|href)="(?:\.\./)?(?:js|css)/[^"?]+)\?v=[0-9]+"')


def html_files() -> list[Path]:
    files = [ROOT / "docs" / "index.html", ROOT / "docs" / "admin.html"]
    archive_dir = ROOT / "docs" / "archive"
    if archive_dir.exists():
        files.extend(sorted(archive_dir.glob("*.html")))
    return files


def write_site_config_js(cfg: dict) -> None:
    body = json.dumps(cfg, indent=2)
    OUT.write_text(
        "// Auto-generated from docs/site-config.json — run: python3 scripts/sync_site_config.py\n"
        f"window.SiteConfig = {body};\n"
        "var MD_VERCEL_ORIGIN = SiteConfig.vercelOrigin;\n"
        "var MD_ASSET_VERSION = SiteConfig.assetVersion;\n"
    )
    print(f"Wrote {OUT}")


def sync_html_versions(version: str) -> None:
    for path in html_files():
        if not path.exists():
            continue
        text = path.read_text()
        new_text, n = ASSET_TAG_RE.subn(rf'\1?v={version}"', text)
        if new_text != text:
            path.write_text(new_text)
            print(f"Updated {n} asset tags in {path.relative_to(ROOT)} -> ?v={version}")
        else:
            print(f"{path.relative_to(ROOT)}: {n} asset tags already at ?v={version}")


def main() -> None:
    cfg = json.loads(SRC.read_text())
    write_site_config_js(cfg)
    version = str(cfg.get("assetVersion", "")).strip()
    if version:
        sync_html_versions(version)
    else:
        print("WARNING: assetVersion missing from site-config.json; skipped HTML sync")


if __name__ == "__main__":
    main()
