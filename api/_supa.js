// Shared helper for the reader-engagement write endpoints.
// Inserts a row into a Supabase table via its PostgREST API using raw fetch,
// so we add no npm dependency to this no-build project. The key used is the
// public "anon"/publishable key (safe to expose); the database's row-level
// security only permits INSERT into these tables, never SELECT, so a leaked
// key cannot read anyone's submissions.
//
// Files prefixed with "_" are not exposed as routes by Vercel.

// Defaults are safe to commit: the URL is public and the key is the Supabase
// "anon" key, designed for public clients and limited by RLS to INSERT-only on
// these three tables. We use the legacy anon JWT (not the sb_publishable_ key)
// because PostgREST derives the role from the JWT claims in the Authorization
// header; a non-JWT publishable key fails role resolution there. Set the env
// vars to rotate without a code change.
const SUPABASE_URL = process.env.SUPABASE_URL || "https://conjziylfpvuuwkmcqsh.supabase.co";
const SUPABASE_KEY =
  process.env.SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNvbmp6aXlsZnB2dXV3a21jcXNoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk5MDQ3ODcsImV4cCI6MjA5NTQ4MDc4N30.00izKhnYOro7A8VoGTj47zkCWntIJ62Uynpg48id_4I";

export function cors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

// Vercel's Node runtime usually pre-parses JSON bodies; fall back to reading the
// raw stream if it didn't (e.g. missing/odd content-type).
export async function readJsonBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") {
    try { return JSON.parse(req.body || "{}"); } catch (_) { return {}; }
  }
  return await new Promise((resolve) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => { try { resolve(JSON.parse(data || "{}")); } catch (_) { resolve({}); } });
    req.on("error", () => resolve({}));
  });
}

export function str(v, max) {
  return v == null ? null : String(v).slice(0, max);
}

// Read-only probe used by /api/health to confirm PostgREST can see a table.
// A SELECT as anon returns 200 (empty, due to RLS) when the schema cache is
// healthy, or 404 PGRST205 when the cache is stale.
export async function probe(table) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${table}?limit=1`, {
    headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` },
  });
  let body = "";
  try { body = await r.text(); } catch (_) {}
  return { status: r.status, body: body.slice(0, 160) };
}

export async function insert(table, row) {
  if (!SUPABASE_URL || !SUPABASE_KEY) throw new Error("supabase env not configured");
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify(row),
  });
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    // Surface the real reason in Vercel runtime logs (the handler only returns a
    // generic 502 to the client).
    console.error(`supabase insert failed [${table}] ${r.status}: ${t.slice(0, 300)}`);
    throw new Error(`supabase ${r.status}`);
  }
}
