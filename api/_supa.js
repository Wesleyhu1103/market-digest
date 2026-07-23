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
import crypto from "crypto";

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

export function cors(res, methods = "GET, POST, OPTIONS") {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", methods);
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
}

export function authorizeAdmin(req) {
  const secret = process.env.FEEDBACK_ADMIN_SECRET;
  if (!secret) return false;
  const auth = req.headers.authorization || "";
  return auth === `Bearer ${secret}`;
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
    `alter table public.feedback add column if not exists processed_at timestamptz`,
    `create table if not exists public.feedback_proposals (
      id bigint generated always as identity primary key,
      created_at timestamptz not null default now(),
      title text not null,
      summary text,
      category text not null,
      status text not null default 'pending',
      source_feedback_ids bigint[] not null default '{}',
      vote_count int not null default 0,
      reject_reason text)`,
    `create table if not exists public.proposal_votes (
      id bigint generated always as identity primary key,
      created_at timestamptz not null default now(),
      proposal_id bigint not null references public.feedback_proposals(id) on delete cascade,
      voter_hash text not null,
      unique (proposal_id, voter_hash))`,
    `create index if not exists idx_feedback_proposals_status on public.feedback_proposals(status)`,
    `create index if not exists idx_feedback_unprocessed on public.feedback(processed_at) where processed_at is null`,
    `create table if not exists public.maintenance_flags (
      id bigint generated always as identity primary key,
      created_at timestamptz not null default now(),
      last_seen timestamptz not null default now(),
      seen_count int not null default 1,
      dedupe_key text unique,
      source text not null,
      severity text not null default 'warning',
      title text not null,
      detail text,
      url text,
      status text not null default 'open',
      resolved_at timestamptz)`,
    `create index if not exists idx_maintenance_flags_status on public.maintenance_flags(status)`,
    `alter table public.feedback enable row level security`,
    `alter table public.quiz_results enable row level security`,
    `alter table public.verdict_notes enable row level security`,
    `alter table public.feedback_proposals enable row level security`,
    `alter table public.proposal_votes enable row level security`,
    `alter table public.maintenance_flags enable row level security`,
  ];
  for (const stmt of stmts) await s.unsafe(stmt);
}

export async function listApprovedProposals() {
  const s = db();
  return s`
    select id, title, summary, category, vote_count, created_at
    from public.feedback_proposals
    where status = 'approved'
    order by vote_count desc, created_at desc`;
}

export async function listProposalsAdmin(statusFilter) {
  const s = db();
  if (statusFilter) {
    return s`
      select p.id, p.title, p.summary, p.category, p.status, p.vote_count,
             p.source_feedback_ids, p.reject_reason, p.created_at
      from public.feedback_proposals p
      where p.status = ${statusFilter}
      order by p.created_at desc`;
  }
  return s`
    select p.id, p.title, p.summary, p.category, p.status, p.vote_count,
           p.source_feedback_ids, p.reject_reason, p.created_at
    from public.feedback_proposals p
    order by p.created_at desc`;
}

export async function getFeedbackByIds(ids) {
  if (!ids || !ids.length) return [];
  const s = db();
  return s`
    select id, digest_date, missing, "open", created_at
    from public.feedback
    where id = any(${ids})`;
}

export async function listRawFeedback(sinceDays) {
  const s = db();
  if (sinceDays) {
    return s`
      select id, digest_date, missing, "open", created_at, processed_at
      from public.feedback
      where created_at >= now() - (${sinceDays} || ' days')::interval
      order by created_at desc`;
  }
  return s`
    select id, digest_date, missing, "open", created_at, processed_at
    from public.feedback
    order by created_at desc
    limit 200`;
}

export async function listUnprocessedFeedback() {
  const s = db();
  return s`
    select id, digest_date, missing, "open", created_at
    from public.feedback
    where processed_at is null
    order by created_at asc`;
}

export async function insertProposal(r) {
  const s = db();
  const rows = await s`
    insert into public.feedback_proposals
      (title, summary, category, status, source_feedback_ids)
    values (${r.title}, ${r.summary}, ${r.category}, ${r.status || "pending"},
            ${r.source_feedback_ids || []})
    returning id`;
  return rows[0].id;
}

export async function markFeedbackProcessed(ids) {
  if (!ids || !ids.length) return;
  const s = db();
  await s`
    update public.feedback
    set processed_at = now()
    where id = any(${ids})`;
}

export async function updateProposalStatus(ids, status, rejectReason) {
  if (!ids || !ids.length) return;
  const s = db();
  if (rejectReason) {
    await s`
      update public.feedback_proposals
      set status = ${status}, reject_reason = ${rejectReason}
      where id = any(${ids})`;
  } else {
    await s`
      update public.feedback_proposals
      set status = ${status}, reject_reason = null
      where id = any(${ids})`;
  }
}

export async function getTopVotedProposals(limit = 10) {
  const s = db();
  return s`
    select id, title, category, vote_count
    from public.feedback_proposals
    where status = 'approved'
    order by vote_count desc, created_at desc
    limit ${limit}`;
}

export async function castProposalVote(proposalId, voterHash, action) {
  const s = db();
  const pid = Number(proposalId);
  if (!Number.isFinite(pid) || pid <= 0) throw new Error("invalid proposal id");
  if (!voterHash || voterHash.length < 8) throw new Error("invalid voter hash");

  const approved = await s`
    select id from public.feedback_proposals
    where id = ${pid} and status = 'approved'`;
  if (!approved.length) throw new Error("proposal not found or not approved");

  if (action === "remove") {
    await s`delete from public.proposal_votes
            where proposal_id = ${pid} and voter_hash = ${voterHash}`;
    await s`update public.feedback_proposals
            set vote_count = (select count(*)::int from public.proposal_votes where proposal_id = ${pid})
            where id = ${pid}`;
    const rows = await s`
      select vote_count from public.feedback_proposals where id = ${pid}`;
    return { voted: false, voteCount: rows[0].vote_count };
  }

  await s`
    insert into public.proposal_votes (proposal_id, voter_hash)
    values (${pid}, ${voterHash})
    on conflict (proposal_id, voter_hash) do nothing`;
  await s`update public.feedback_proposals
          set vote_count = (select count(*)::int from public.proposal_votes where proposal_id = ${pid})
          where id = ${pid}`;
  const rows = await s`
    select vote_count from public.feedback_proposals where id = ${pid}`;
  return { voted: true, voteCount: rows[0].vote_count };
}

export function voterHashFromRequest(req, clientId) {
  const ip = (req.headers["x-forwarded-for"] || req.socket?.remoteAddress || "")
    .toString()
    .split(",")[0]
    .trim();
  const ua = (req.headers["user-agent"] || "").slice(0, 200);
  const cid = (clientId || "").slice(0, 64);
  return crypto.createHash("sha256").update(`${ip}|${ua}|${cid}`).digest("hex");
}

// ── Site maintenance flags (monitor → admin pipeline) ──────────────────
// Monitors (watchdog, feed check, bot-PR mirror) upsert flags keyed by
// dedupe_key; a recurrence of a RESOLVED flag reopens it — that recurrence
// is the signal that an earlier fix didn't hold.
export async function upsertMaintenanceFlag(r) {
  const s = db();
  if (r.dedupe_key) {
    const rows = await s`
      insert into public.maintenance_flags
        (dedupe_key, source, severity, title, detail, url)
      values (${r.dedupe_key}, ${r.source}, ${r.severity || "warning"},
              ${r.title}, ${r.detail || null}, ${r.url || null})
      on conflict (dedupe_key) do update set
        last_seen = now(),
        seen_count = public.maintenance_flags.seen_count + 1,
        severity = excluded.severity,
        title = excluded.title,
        detail = excluded.detail,
        url = excluded.url,
        status = case when public.maintenance_flags.status = 'resolved'
                      then 'open' else public.maintenance_flags.status end,
        resolved_at = case when public.maintenance_flags.status = 'resolved'
                           then null else public.maintenance_flags.resolved_at end
      returning id, status, seen_count`;
    return rows[0];
  }
  const rows = await s`
    insert into public.maintenance_flags (source, severity, title, detail, url)
    values (${r.source}, ${r.severity || "warning"}, ${r.title},
            ${r.detail || null}, ${r.url || null})
    returning id, status, seen_count`;
  return rows[0];
}

export async function listMaintenanceFlags(statusFilter) {
  const s = db();
  if (statusFilter) {
    return s`
      select id, created_at, last_seen, seen_count, dedupe_key, source,
             severity, title, detail, url, status, resolved_at
      from public.maintenance_flags
      where status = ${statusFilter}
      order by last_seen desc
      limit 200`;
  }
  return s`
    select id, created_at, last_seen, seen_count, dedupe_key, source,
           severity, title, detail, url, status, resolved_at
    from public.maintenance_flags
    order by (status = 'open') desc, last_seen desc
    limit 200`;
}

export async function setMaintenanceStatus(ids, status) {
  if (!ids || !ids.length) return;
  const s = db();
  await s`
    update public.maintenance_flags
    set status = ${status},
        resolved_at = case when ${status} = 'resolved' then now() else null end
    where id = any(${ids})`;
}

// Used by /api/health to confirm the DB connection works end to end.
export async function probe() {
  const s = db();
  const rows = await s`select
    (select count(*)::int from public.feedback)           as feedback,
    (select count(*)::int from public.quiz_results)       as quiz_results,
    (select count(*)::int from public.verdict_notes)      as verdict_notes,
    (select count(*)::int from public.feedback_proposals) as feedback_proposals,
    (select count(*)::int from public.proposal_votes)     as proposal_votes`;
  return rows[0];
}
