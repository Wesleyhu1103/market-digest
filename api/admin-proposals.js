// GET /api/admin-proposals — pending/approved proposals with source feedback.
// POST /api/admin-proposals — approve/reject proposals by id, or
//   { action: "process" } to cluster unprocessed feedback into proposals.
//
// Auth (two tiers, see _auth.js):
//  - Authorization: Bearer <FEEDBACK_ADMIN_SECRET> — full access (admin page).
//  - x-maintenance-token: <MAINTENANCE_TOKEN|CRON_SECRET> — monitor scope,
//    limited to GET ?status=pending and POST {action:"process"}: exactly what
//    the process-feedback workflow needs, so the pipeline runs on the repo
//    secret that already exists instead of a hand-synced admin bearer copy.
//    The pending list a monitor can read is the same content that workflow
//    publishes into the public feedback-review issue; raw feedback and
//    approve/reject stay admin-only.
import {
  cors,
  readJsonBody,
  authorizeAdmin,
  ensureSchema,
  listProposalsAdmin,
  getFeedbackByIds,
  updateProposalStatus,
} from "./_supa.js";
import { authorizeMonitor, monitorMayProposals } from "./_auth.js";
import { processFeedback } from "./_process_feedback.js";

async function enrichWithSources(proposals) {
  const allIds = [...new Set(proposals.flatMap((p) => p.source_feedback_ids || []))];
  const feedback = allIds.length ? await getFeedbackByIds(allIds) : [];
  const byId = Object.fromEntries(feedback.map((f) => [Number(f.id), f]));
  return proposals.map((p) => ({
    id: Number(p.id),
    title: p.title,
    summary: p.summary,
    category: p.category,
    status: p.status,
    voteCount: p.vote_count,
    rejectReason: p.reject_reason,
    createdAt: p.created_at,
    sourceFeedbackIds: p.source_feedback_ids || [],
    sources: (p.source_feedback_ids || []).map((fid) => {
      const f = byId[Number(fid)];
      if (!f) return { id: fid, text: "(missing)", date: null };
      const text = [f.missing, f.open].filter(Boolean).join(" | ").trim();
      return { id: Number(f.id), text, date: f.digest_date || f.created_at };
    }),
  }));
}

export default async function handler(req, res) {
  cors(res, "GET, POST, OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, x-maintenance-token"
  );
  if (req.method === "OPTIONS") return res.status(204).end();

  const isAdmin = authorizeAdmin(req);
  const isMonitor = !isAdmin && authorizeMonitor(req);
  if (!isAdmin && !isMonitor) return res.status(401).json({ error: "unauthorized" });

  try {
    if (req.method === "GET") {
      const status = req.query?.status || null;
      // Scope decisions come before any DB work: an out-of-scope monitor
      // call must 403, not surface as a 502 when the DB is unreachable.
      if (isMonitor && !monitorMayProposals("GET", { status })) {
        return res
          .status(403)
          .json({ error: "monitor token is limited to GET ?status=pending" });
      }
      await ensureSchema();
      const rows = await listProposalsAdmin(status);
      const proposals = await enrichWithSources(rows);
      res.status(200).json({ proposals });
      return;
    }

    if (req.method === "POST") {
      const b = (await readJsonBody(req)) || {};
      if (isMonitor && !monitorMayProposals("POST", { action: b.action })) {
        return res
          .status(403)
          .json({ error: 'monitor token is limited to POST {"action":"process"}' });
      }
      await ensureSchema();

      // action: "process" — cluster unprocessed feedback into pending
      // proposals. Folded in from the former /api/admin-process-feedback
      // function: Vercel Hobby caps a deployment at 12 serverless
      // functions, and that 13th file broke the whole deploy.
      if (b.action === "process") {
        const result = await processFeedback();
        res.status(200).json(result);
        return;
      }

      const ids = Array.isArray(b.ids) ? b.ids.map(Number).filter((n) => n > 0) : [];
      if (!ids.length) return res.status(400).json({ error: "ids required" });

      if (b.action === "approve") {
        await updateProposalStatus(ids, "approved");
        res.status(200).json({ ok: true, approved: ids });
        return;
      }
      if (b.action === "reject") {
        await updateProposalStatus(ids, "rejected", b.reason || null);
        res.status(200).json({ ok: true, rejected: ids });
        return;
      }
      return res.status(400).json({ error: "action must be approve, reject, or process" });
    }

    res.status(405).json({ error: "method not allowed" });
  } catch (e) {
    console.error("admin proposals failed:", e && e.message);
    res.status(502).json({ error: "admin failed" });
  }
}
