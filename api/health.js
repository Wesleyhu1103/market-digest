// GET /api/health — reports whether PostgREST can see each table.
// Used to verify the Supabase schema cache without a browser submission.
import { cors, probe } from "./_supa.js";

export default async function handler(req, res) {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  const tables = ["feedback", "quiz_results", "verdict_notes"];
  const out = {};
  for (const t of tables) {
    try {
      out[t] = await probe(t);
    } catch (e) {
      out[t] = { status: "err", body: String(e).slice(0, 120) };
    }
  }
  res.status(200).json(out);
}
