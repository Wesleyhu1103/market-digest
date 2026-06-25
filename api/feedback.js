// POST /api/feedback — persists the "What did we miss / open feedback" form.
// Body: { date, submittedAt, missing, open, ...ratingGroups }
import { cors, readJsonBody, str, insert } from "./_supa.js";

export default async function handler(req, res) {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method not allowed" });

  const b = (await readJsonBody(req)) || {};
  const { date, submittedAt, missing, open, ...ratings } = b;

  try {
    await insert("feedback", {
      digest_date: str(date, 10),
      missing: str(missing, 5000),
      open: str(open, 5000),
      ratings: ratings && Object.keys(ratings).length ? ratings : null,
      user_agent: str(req.headers["user-agent"], 400),
    });
    res.status(204).end();
  } catch (e) {
    res.status(502).json({ error: "insert failed" });
  }
}
