// Vercel Cron backup for digest-watchdog.yml when GitHub's scheduler lags or skips.
// Polls whether docs/index.html is behind today (US/Eastern) and dispatches
// publish-digest.yml via the GitHub API when stale.
//
// Env (Vercel project settings):
//   CRON_SECRET   — required; Vercel sends Authorization: Bearer <CRON_SECRET>
//   GITHUB_TOKEN  — PAT or fine-grained token with actions:write on this repo

const REPO = "Wesleyhu1103/market-digest";
const INDEX_URL =
  "https://raw.githubusercontent.com/Wesleyhu1103/market-digest/main/docs/index.html";

function todayEasternIso() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const y = parts.find((p) => p.type === "year")?.value;
  const m = parts.find((p) => p.type === "month")?.value;
  const d = parts.find((p) => p.type === "day")?.value;
  return `${y}-${m}-${d}`;
}

function digestDateFromHtml(html) {
  const meta = html.match(/date:\s*'(\d{4}-\d{2}-\d{2})'/);
  if (meta) return meta[1];
  const h1 = html.match(/<h1>([^<]+)<\/h1>/);
  if (!h1) return null;
  const months = {
    January: 1, February: 2, March: 3, April: 4, May: 5, June: 6,
    July: 7, August: 8, September: 9, October: 10, November: 11, December: 12,
  };
  const m = h1[1].trim().match(/^(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})$/);
  if (!m || !months[m[2]]) return null;
  const mo = String(months[m[2]]).padStart(2, "0");
  const day = String(m[3]).padStart(2, "0");
  return `${m[4]}-${mo}-${day}`;
}

function authorizeCron(req) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false;
  const auth = req.headers.authorization || "";
  return auth === `Bearer ${secret}`;
}

async function publishInProgress(token) {
  const url =
    `https://api.github.com/repos/${REPO}/actions/workflows/publish-digest.yml/runs?status=in_progress&per_page=1`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!res.ok) throw new Error(`github runs ${res.status}`);
  const body = await res.json();
  return (body.total_count || 0) > 0;
}

async function dispatchPublish(token) {
  const url = `https://api.github.com/repos/${REPO}/actions/workflows/publish-digest.yml/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  if (res.status !== 204) {
    const text = await res.text();
    throw new Error(`dispatch ${res.status}: ${text}`);
  }
}

export default async function handler(req, res) {
  if (req.method !== "GET" && req.method !== "POST") {
    res.status(405).json({ error: "method not allowed" });
    return;
  }
  if (!authorizeCron(req)) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  const today = todayEasternIso();
  let digestDate = null;
  try {
    const htmlRes = await fetch(INDEX_URL, { cache: "no-store" });
    if (!htmlRes.ok) throw new Error(`index fetch ${htmlRes.status}`);
    digestDate = digestDateFromHtml(await htmlRes.text());
  } catch (e) {
    res.status(502).json({ ok: false, error: (e && e.message) || "index fetch failed" });
    return;
  }

  const stale = !digestDate || digestDate < today;
  if (!stale) {
    console.log(`[cron-watchdog] current today=${today} digestDate=${digestDate}`);
    res.status(200).json({ ok: true, action: "skip", today, digestDate, stale: false });
    return;
  }

  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    // Non-2xx so Vercel flags the cron run as failed instead of silently no-oping.
    console.error(
      `[cron-watchdog] STALE but cannot dispatch: GITHUB_TOKEN not set on Vercel. ` +
        `today=${today} digestDate=${digestDate}. Digest will only update if GitHub's own cron fires.`
    );
    res.status(503).json({
      ok: false,
      action: "stale",
      today,
      digestDate,
      error: "GITHUB_TOKEN not configured on Vercel",
    });
    return;
  }

  try {
    if (await publishInProgress(token)) {
      console.log(`[cron-watchdog] stale but publish already in progress; today=${today}`);
      res.status(200).json({
        ok: true,
        action: "skip_in_progress",
        today,
        digestDate,
        stale: true,
      });
      return;
    }
    await dispatchPublish(token);
    console.log(`[cron-watchdog] dispatched publish; today=${today} digestDate=${digestDate}`);
    res.status(200).json({ ok: true, action: "dispatched", today, digestDate, stale: true });
  } catch (e) {
    console.error(
      `[cron-watchdog] dispatch FAILED: ${(e && e.message) || e} today=${today} digestDate=${digestDate}`
    );
    res.status(502).json({
      ok: false,
      action: "dispatch_failed",
      today,
      digestDate,
      error: (e && e.message) || "dispatch failed",
    });
  }
}
