// Vercel serverless function: cached Yahoo Finance quote proxy.
//
// The static page (served from GitHub Pages) can't call query1.finance.yahoo.com
// directly because of CORS, so today it routes through flaky public proxies
// (corsproxy.io, allorigins, ...). This endpoint replaces the unreliable first
// hop with our own origin: it fetches Yahoo server-side (no CORS there), caches
// at Vercel's edge for a few seconds, and returns the raw Yahoo JSON unchanged
// so the existing client parser (parseYahoo) is a drop-in consumer.
//
// Safety: this is NOT an open proxy. The `url` param is validated to point at a
// Yahoo Finance host before we fetch it, so it can't be used to proxy arbitrary
// requests (SSRF). Read-only GET of public market data, so CORS is wide open.

const ALLOWED_HOSTS = new Set([
  "query1.finance.yahoo.com",
  "query2.finance.yahoo.com",
]);

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

  const raw = req.query.url;
  if (!raw || typeof raw !== "string") {
    res.status(400).json({ error: "missing url param" });
    return;
  }

  let target;
  try {
    target = new URL(raw);
  } catch (_) {
    res.status(400).json({ error: "invalid url" });
    return;
  }
  if (target.protocol !== "https:" || !ALLOWED_HOSTS.has(target.hostname)) {
    res.status(403).json({ error: "host not allowed" });
    return;
  }

  try {
    const upstream = await fetch(target.toString(), {
      headers: {
        // Yahoo rejects requests without a browser-ish UA.
        "User-Agent":
          "Mozilla/5.0 (compatible; market-digest/1.0; +https://wesleyhu1103.github.io/market-digest)",
        Accept: "application/json",
      },
    });
    if (!upstream.ok) {
      res.status(502).json({ error: "upstream " + upstream.status });
      return;
    }
    const json = await upstream.json();
    // Edge-cache so the 60s client tier hits cache, not Yahoo, on every cycle.
    res.setHeader("Cache-Control", "s-maxage=30, stale-while-revalidate=60");
    res.status(200).json(json);
  } catch (e) {
    res.status(502).json({ error: "fetch failed" });
  }
}
