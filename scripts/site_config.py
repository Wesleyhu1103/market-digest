"""Load docs/site-config.json — shared constants for Python pipeline scripts."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "docs" / "site-config.json"


@lru_cache(maxsize=1)
def load_site_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def fred_series() -> dict[str, str]:
    return dict(load_site_config()["fred"]["series"])


def fred_days() -> int:
    return int(load_site_config()["fred"]["days"])


def repair_chart_heights() -> dict[str, int]:
    return dict(load_site_config()["repair"]["chartHeights"])


def repair_thresholds() -> tuple[int, int]:
    r = load_site_config()["repair"]
    return int(r["minBullOn"]), int(r["minShowBull"])
