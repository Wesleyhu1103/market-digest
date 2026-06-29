// POST /api/verdict-note — saves a reader's post-close verdict note.
// Body: { date, note }
import { cors, readJsonBody, str, insertVerdict } from "./_supa.js";

export default async function handler(req, res) {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method not allowed" });

  const b = (await readJsonBody(req)) || {};
  const note = str(b.note, 5000);
  if (!note || !note.trim()) return res.status(400).json({ error: "empty note" });

  try {
    await insertVerdict({ digest_date: str(b.date, 10), note });
    res.status(204).end();
  } catch (e) {
    console.error("verdict insert failed:", e && e.message);
    res.status(502).json({ error: "insert failed" });
  }
}
