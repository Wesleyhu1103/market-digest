// GET /api/health — ensures the schema exists, then reports row counts.
// Hitting this once sets up the tables in the connected database.
import { cors, ensureSchema, probe } from "./_supa.js";

export default async function handler(req, res) {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    await ensureSchema();
    const counts = await probe();
    res.status(200).json({ ok: true, counts });
  } catch (e) {
    res.status(502).json({ ok: false, error: (e && e.message) || "db error" });
  }
}
