// Shared DB helper for the reader-engagement write endpoints.
//
// We connect DIRECTLY to Postgres (via the Supabase transaction pooler) instead
// of going through PostgREST (/rest/v1), because this project's PostgREST schema
// cache got wedged after the project was unpaused and would not recover. A
// direct connection is immune to that entire class of problem.
//
// Requires the env var SUPABASE_DB_URL — the Supabase "Transaction pooler"
// connection string (port 6543), e.g.
//   postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
// Set it in the Vercel project's Environment Variables.
//
// Files prefixed with "_" are not exposed as routes by Vercel.

import postgres from "postgres";

const DB_URL = process.env.SUPABASE_DB_URL || process.env.DATABASE_URL || "";

let sql;
function db() {
  if (!DB_URL) throw new Error("SUPABASE_DB_URL not configured");
  if (!sql) {
    // prepare:false is required for the transaction-mode pooler; max:1 keeps a
    // single short-lived connection per warm serverless instance.
    sql = postgres(DB_URL, {
      prepare: false,
      max: 1,
      idle_timeout: 20,
      connect_timeout: 10,
      ssl: "require",
    });
  }
  return sql;
}

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

export async function insertFeedback(r) {
  const s = db();
  await s`insert into public.feedback (digest_date, missing, "open", ratings, user_agent)
          values (${r.digest_date}, ${r.missing}, ${r.open},
                  ${r.ratings ? s.json(r.ratings) : null}, ${r.user_agent})`;
}

export async function insertQuiz(r) {
  const s = db();
  await s`insert into public.quiz_results (digest_date, question_index, picked, correct, is_correct)
          values (${r.digest_date}, ${r.question_index}, ${r.picked}, ${r.correct}, ${r.is_correct})`;
}

export async function insertVerdict(r) {
  const s = db();
  await s`insert into public.verdict_notes (digest_date, note) values (${r.digest_date}, ${r.note})`;
}

// Used by /api/health to confirm the DB connection works end to end.
export async function probe() {
  const s = db();
  const rows = await s`select
    (select count(*)::int from public.feedback)      as feedback,
    (select count(*)::int from public.quiz_results)  as quiz_results,
    (select count(*)::int from public.verdict_notes) as verdict_notes`;
  return rows[0];
}
