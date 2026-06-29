// GET /api/health — confirms the direct DB connection works and reports row counts.
import { cors, probe } from "./_supa.js";

export default async function handler(req, res) {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const counts = await probe();
    res.status(200).json({ ok: true, counts });
  } catch (e) {
    res.status(502).json({ ok: false, error: (e && e.message) || "db error" });
  }
}
