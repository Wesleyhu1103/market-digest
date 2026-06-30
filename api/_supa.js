// Shared DB helper for the reader-engagement write endpoints.
//
// We connect DIRECTLY to Postgres (via the Supabase transaction pooler) instead
// of going through PostgREST (/rest/v1), because this project's PostgREST schema
// cache got wedged after the project was unpaused and would not recover. A
// direct connection is immune to that entire class of problem.
//
// Connection comes from POSTGRES_URL, which the Vercel<>Supabase Marketplace
// integration already provisions for this project (pooled, port 6543). No new
// env var needed. SUPABASE_DB_URL/DATABASE_URL are accepted as overrides.
//
// Files prefixed with "_" are not exposed as routes by Vercel.

import postgres from "postgres";

const DB_URL =
  process.env.SUPABASE_DB_URL ||
  process.env.POSTGRES_URL ||
  process.env.DATABASE_URL ||
  "";

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

// Idempotently create the tables in whatever database POSTGRES_URL points at.
// Runs as the integration's postgres role (table owner), so inserts bypass RLS;
// RLS is enabled with no policies so the public data API can't read/write them.
export async function ensureSchema() {
  const s = db();
  const stmts = [
    `create table if not exists public.feedback (
      id bigint generated always as identity primary key,
      created_at timestamptz not null default now(),
      digest_date date, missing text, "open" text, ratings jsonb, user_agent text)`,
    `create table if not exists public.quiz_results (
      id bigint generated always as identity primary key,
      created_at timestamptz not null default now(),
      digest_date date, question_index smallint, picked text, correct text, is_correct boolean)`,
    `create table if not exists public.verdict_notes (
      id bigint generated always as identity primary key,
      created_at timestamptz not null default now(),
      digest_date date, note text)`,
    `alter table public.feedback enable row level security`,
    `alter table public.quiz_results enable row level security`,
    `alter table public.verdict_notes enable row level security`,
  ];
  for (const stmt of stmts) await s.unsafe(stmt);
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
