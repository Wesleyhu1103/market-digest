// POST /api/quiz — records one quiz answer.
// Body: { date, questionIndex, picked, correct, isCorrect }
import { cors, readJsonBody, str, insertQuiz } from "./_supa.js";

export default async function handler(req, res) {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method not allowed" });

  const b = (await readJsonBody(req)) || {};
  try {
    await insertQuiz({
      digest_date: str(b.date, 10),
      question_index: Number.isInteger(b.questionIndex) ? b.questionIndex : null,
      picked: str(b.picked, 8),
      correct: str(b.correct, 8),
      is_correct: typeof b.isCorrect === "boolean" ? b.isCorrect : null,
    });
    res.status(204).end();
  } catch (e) {
    console.error("quiz insert failed:", e && e.message);
    res.status(502).json({ error: "insert failed" });
  }
}
