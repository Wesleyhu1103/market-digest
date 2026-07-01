// GET /api/admin-feedback — raw reader feedback submissions (admin only).
// Query: ?since=7 (optional days)
// Auth: Authorization: Bearer <FEEDBACK_ADMIN_SECRET>
import {
  cors,
  authorizeAdmin,
  ensureSchema,
  listRawFeedback,
} from "./_supa.js";

export default async function handler(req, res) {
  cors(res, "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "method not allowed" });
  if (!authorizeAdmin(req)) return res.status(401).json({ error: "unauthorized" });

  try {
    await ensureSchema();
    const sinceRaw = req.query?.since;
    const sinceDays = sinceRaw != null && sinceRaw !== "" ? Number(sinceRaw) : null;
    const rows = await listRawFeedback(
      Number.isFinite(sinceDays) && sinceDays > 0 ? sinceDays : null
    );
    const feedback = rows.map((r) => ({
      id: Number(r.id),
      digestDate: r.digest_date,
      missing: r.missing,
      open: r.open,
      createdAt: r.created_at,
      processedAt: r.processed_at,
    }));
    res.status(200).json({ feedback });
  } catch (e) {
    console.error("admin feedback failed:", e && e.message);
    res.status(502).json({ error: "admin failed" });
  }
}
