// Live FRED macro payload for chart auto-refresh on Vercel.
// Static docs/fred-data.json is only refreshed at publish time; this endpoint
// re-fetches from the FRED API (when FRED_API_KEY is set) so credit/stress
// series pick up the latest published observations between publishes.

import fs from "fs";
import path from "path";

function loadSiteConfig() {
  const cfgPath = path.join(process.cwd(), "docs", "site-config.json");
  return JSON.parse(fs.readFileSync(cfgPath, "utf8"));
}

const { fred: fredCfg, vercelOrigin } = loadSiteConfig();
const SERIES = fredCfg.series;
const DAYS = fredCfg.days;
const UA = `Mozilla/5.0 (compatible; market-digest/1.0; +${vercelOrigin})`;

function startDate() {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - DAYS);
  return d.toISOString().slice(0, 10);
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

async function fetchFredSeries(apiKey, seriesId) {
  const start = startDate();
  const end = todayStr();
  const url =
    "https://api.stlouisfed.org/fred/series/observations" +
    `?series_id=${encodeURIComponent(seriesId)}` +
    `&api_key=${encodeURIComponent(apiKey)}` +
    "&file_type=json" +
    `&observation_start=${start}` +
    `&observation_end=${end}`;

  const res = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`FRED ${seriesId} HTTP ${res.status}`);

  const json = await res.json();
  const rows = [];
  for (const obs of json.observations || []) {
    const date = obs.date;
    const val = obs.value;
    if (!date || val == null || val === ".") continue;
    const v = Number(val);
    if (!Number.isFinite(v)) continue;
    if (date < start) continue;
    rows.push({ date, value: Math.round(v * 10000) / 10000 });
  }
  return rows;
}

async function fetchFredCsv(seriesId) {
  const start = startDate();
  const end = todayStr();
  const url =
    "https://fred.stlouisfed.org/graph/fredgraph.csv" +
    `?id=${encodeURIComponent(seriesId)}` +
    `&cosd=${start}&coed=${end}`;
  const res = await fetch(url, {
    headers: { "User-Agent": UA, Accept: "text/csv,*/*" },
  });
  if (!res.ok) throw new Error(`FRED CSV ${seriesId} HTTP ${res.status}`);
  const text = await res.text();
  const rows = [];
  for (const line of text.trim().split("\n").slice(1)) {
    const idx = line.indexOf(",");
    if (idx < 0) continue;
    const date = line.slice(0, idx).trim();
    const val = line.slice(idx + 1).trim();
    if (!date || !val || val === ".") continue;
    const v = Number(val);
    if (!Number.isFinite(v) || date < start) continue;
    rows.push({ date, value: Math.round(v * 10000) / 10000 });
  }
  return rows;
}

async function fetchAllFred(apiKey) {
  const keys = Object.keys(SERIES);
  const fetcher = apiKey
    ? (id) => fetchFredSeries(apiKey, id)
    : (id) => fetchFredCsv(id);
  const results = await Promise.all(
    keys.map((key) => fetcher(SERIES[key]).catch(() => null))
  );
  const data = {};
  let fetched = 0;
  for (let i = 0; i < keys.length; i++) {
    if (results[i] && results[i].length) {
      data[keys[i]] = results[i];
      fetched++;
    }
  }
  return { data, fetched };
}

async function mergeStatic(req, data) {
  try {
    const prev = await loadStatic(req);
    if (prev.fred) {
      if (!data.DGS2 && prev.fred.DGS2) data.DGS2 = prev.fred.DGS2;
      if (!data.DGS10 && prev.fred.DGS10) data.DGS10 = prev.fred.DGS10;
      if (!data.DGS30 && prev.fred.DGS30) data.DGS30 = prev.fred.DGS30;
    }
    if (!data.DCOILBRENTEU && prev.brent) data.DCOILBRENTEU = prev.brent;
    if (prev.credit) {
      if (!data.HY_OAS && prev.credit.HY_OAS) data.HY_OAS = prev.credit.HY_OAS;
      if (!data.IG_OAS && prev.credit.IG_OAS) data.IG_OAS = prev.credit.IG_OAS;
      if (!data.VIX && prev.credit.VIX) data.VIX = prev.credit.VIX;
      if (!data.TENMINUSTWO && prev.credit.TENMINUSTWO) {
        data.TENMINUSTWO = prev.credit.TENMINUSTWO;
      }
    }
  } catch (_) {
    /* optional */
  }
  return data;
}

async function loadStatic(req) {
  const proto = req.headers["x-forwarded-proto"] || "https";
  const host = req.headers.host;
  const url = host ? `${proto}://${host}/fred-data.json` : "/fred-data.json";
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("static fred-data.json unavailable");
  return res.json();
}

function buildPayload(data) {
  return {
    updated: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    source: "fred-api",
    fred: {
      DGS2: data.DGS2 || [],
      DGS10: data.DGS10 || [],
      DGS30: data.DGS30 || [],
    },
    brent: data.DCOILBRENTEU || [],
    credit: {
      HY_OAS: data.HY_OAS || [],
      IG_OAS: data.IG_OAS || [],
      VIX: data.VIX || [],
      TENMINUSTWO: data.TENMINUSTWO || [],
    },
  };
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "GET") {
    res.status(405).json({ error: "method not allowed" });
    return;
  }

  const apiKey = process.env.FRED_API_KEY || "";

  try {
    const { data, fetched } = await fetchAllFred(apiKey || null);
    if (!fetched) {
      const payload = await loadStatic(req);
      res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=120");
      res.status(200).json(Object.assign({ source: "static-fallback" }, payload));
      return;
    }

    await mergeStatic(req, data);
    const source = apiKey ? "fred-api" : "fred-csv";
    res.setHeader("Cache-Control", "s-maxage=900, stale-while-revalidate=1800");
    res.status(200).json(Object.assign({ source }, buildPayload(data)));
  } catch (_) {
    try {
      const payload = await loadStatic(req);
      res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=120");
      res.status(200).json(Object.assign({ source: "static-fallback" }, payload));
    } catch (e) {
      res.status(502).json({ error: "fred fetch failed" });
    }
  }
}
