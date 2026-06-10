#!/usr/bin/env python3
"""Fetch latest FRED series and write docs/fred-data.json for macro charts.

fred.stlouisfed.org's CSV endpoint intermittently times out from cloud
datacenter IPs (e.g. GitHub Actions runners). Strategy:
  - If FRED_API_KEY is set, use the official API (api.stlouisfed.org) —
    reliable from anywhere; free key at https://fred.stlouisfed.org/docs/api/api_key.html
  - Otherwise fall back to the keyless fredgraph.csv endpoint with retries
  - A series that fails all attempts keeps its previous values from the
    existing fred-data.json instead of blanking the chart
"""
import csv
import io
import json
import os
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
API_KEY = os.environ.get("FRED_API_KEY", "")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    last_err = None
    for attempt in range(4):
        try:
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        except (OSError, TimeoutError) as e:
            last_err = e
            print(f"  retry {attempt + 1}: {e}")
            time.sleep(5 * (attempt + 1))
    raise last_err


def fetch_series(series_id: str) -> list[dict]:
    start = (datetime.now() - timedelta(days=DAYS)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=DAYS)).date()
    rows = []

    if API_KEY:
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={API_KEY}&file_type=json"
            f"&observation_start={start}&observation_end={end}"
        )
        payload = json.loads(_get(url))
        if payload.get("error_code") or "observations" not in payload:
            msg = payload.get("error_message") or "missing observations in FRED API response"
            raise RuntimeError(msg)
        for obs in payload["observations"]:
            date_s, val_s = obs.get("date", ""), obs.get("value", "")
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

    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        f"&cosd={start}&coed={end}"
    )
    raw = _get(url)
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


def load_previous() -> dict:
    try:
        old = json.loads(OUT.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    prev = {}
    for k in ("DGS2", "DGS10", "DGS30"):
        prev[k] = old.get("fred", {}).get(k, [])
    prev["DCOILBRENTEU"] = old.get("brent", [])
    for k in ("HY_OAS", "IG_OAS", "VIX", "TENMINUSTWO"):
        prev[k] = old.get("credit", {}).get(k, [])
    return prev


def main():
    prev = load_previous()
    data = {}
    fetched = 0
    for key, sid in SERIES.items():
        print(f"Fetching {sid}..." + (" (API)" if API_KEY else " (CSV)"))
        try:
            rows = fetch_series(sid)
            if not rows:
                raise RuntimeError("no usable observations returned")
            data[key] = rows
            fetched += 1
            print(f"  {len(data[key])} points (last {data[key][-1]['date'] if data[key] else 'n/a'})")
        except Exception as e:
            data[key] = prev.get(key, [])
            print(f"  FAILED {sid}: {e} — keeping {len(data[key])} previous points")

    if fetched == 0:
        raise SystemExit("ABORT: no FRED series fetched; leaving fred-data.json untouched")

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
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB), {fetched}/{len(SERIES)} series fresh")


if __name__ == "__main__":
    main()
