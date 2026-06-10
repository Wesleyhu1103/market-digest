#!/usr/bin/env python3
"""Fetch latest FRED series and write docs/fred-data.json for macro charts."""
import csv
import io
import json
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

SERIES = {
    "DGS2": "DGS2",
    "DGS10": "DGS10",
    "DGS30": "DGS30",
    "DCOILBRENTEU": "DCOILBRENTEU",
    "HY_OAS": "BAMLH0A0HYM2EY",
    "IG_OAS": "BAMLC0A0CM",
    "VIX": "VIXCLS",
    "TENMINUSTWO": "T10Y2Y",
}

DAYS = 120
OUT = Path(__file__).resolve().parents[1] / "docs" / "fred-data.json"
REQUEST_HEADERS = {"User-Agent": "market-digest/1.0", "Accept": "text/csv,*/*"}


def fetch_series(series_id: str) -> list[dict]:
    start = (datetime.now() - timedelta(days=DAYS)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        f"&cosd={start}&coed={end}"
    )
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    # FRED is intermittently slow; retry transient failures before giving up
    for attempt in range(3):
        try:
            raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
            break
        except (OSError, TimeoutError) as e:
            if attempt == 2:
                raise
            print(f"  retry {attempt + 1} for {series_id}: {e}")
            time.sleep(5 * (attempt + 1))
    cutoff = (datetime.now() - timedelta(days=DAYS)).date()
    rows = []
    for row in csv.DictReader(io.StringIO(raw)):
        date_s = row.get("observation_date") or row.get("DATE") or ""
        val_s = row.get(series_id) or row.get("VALUE") or ""
        if not date_s or val_s in ("", "."):
            continue
        try:
            d = datetime.strptime(date_s[:10], "%Y-%m-%d").date()
            v = float(val_s)
        except ValueError:
            continue
        if d >= cutoff:
            rows.append({"date": d.isoformat(), "value": round(v, 4)})
    return rows


def main():
    data = {}
    for key, sid in SERIES.items():
        print(f"Fetching {sid}...")
        data[key] = fetch_series(sid)
        print(f"  {len(data[key])} points (last {data[key][-1]['date'] if data[key] else 'n/a'})")

    payload = {
        "updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fred": {
            "DGS2": data["DGS2"],
            "DGS10": data["DGS10"],
            "DGS30": data["DGS30"],
        },
        "brent": data["DCOILBRENTEU"],
        "credit": {
            "HY_OAS": data["HY_OAS"],
            "IG_OAS": data["IG_OAS"],
            "VIX": data["VIX"],
            "TENMINUSTWO": data["TENMINUSTWO"],
        },
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
