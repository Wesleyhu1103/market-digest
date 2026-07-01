// GET /api/admin-proposals — pending/approved proposals with source feedback (admin only).
// POST /api/admin-proposals — approve or reject proposals by id.
// Auth: Authorization: Bearer <FEEDBACK_ADMIN_SECRET>
import {
  cors,
  readJsonBody,
  authorizeAdmin,
  ensureSchema,
  listProposalsAdmin,
  getFeedbackByIds,
  updateProposalStatus,
} from "./_supa.js";

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
  if (req.method === "OPTIONS") return res.status(204).end();
  if (!authorizeAdmin(req)) return res.status(401).json({ error: "unauthorized" });

  try {
    await ensureSchema();

    if (req.method === "GET") {
      const status = req.query?.status || null;
      const rows = await listProposalsAdmin(status);
      const proposals = await enrichWithSources(rows);
      res.status(200).json({ proposals });
      return;
    }

    if (req.method === "POST") {
      const b = (await readJsonBody(req)) || {};
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
      return res.status(400).json({ error: "action must be approve or reject" });
    }

    res.status(405).json({ error: "method not allowed" });
  } catch (e) {
    console.error("admin proposals failed:", e && e.message);
    res.status(502).json({ error: "admin failed" });
  }
}
