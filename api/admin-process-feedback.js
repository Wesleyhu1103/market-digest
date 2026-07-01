// POST /api/admin-process-feedback — cluster unprocessed feedback into pending proposals.
// Auth: Authorization: Bearer <FEEDBACK_ADMIN_SECRET>
import { cors, authorizeAdmin } from "./_supa.js";
import { processFeedback } from "./_process_feedback.js";

export default async function handler(req, res) {
  cors(res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method not allowed" });
  if (!authorizeAdmin(req)) return res.status(401).json({ error: "unauthorized" });

  try {
    const result = await processFeedback();
    res.status(200).json(result);
  } catch (e) {
    console.error("process feedback failed:", e && e.message);
    res.status(502).json({ error: "process failed" });
  }
}
