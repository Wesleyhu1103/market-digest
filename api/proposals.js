// GET /api/proposals — approved proposals grouped by category for public voting board.
import { cors, ensureSchema, listApprovedProposals } from "./_supa.js";

const CATEGORY_ORDER = ["coverage", "depth", "format", "sources", "sections", "features"];
const CATEGORY_LABELS = {
  coverage: "Coverage",
  depth: "Depth",
  format: "Format",
  sources: "Sources",
  sections: "Sections",
  features: "Features",
};

export default async function handler(req, res) {
  cors(res, "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "method not allowed" });

  try {
    await ensureSchema();
    const rows = await listApprovedProposals();
    const grouped = {};
    for (const cat of CATEGORY_ORDER) grouped[cat] = [];
    for (const row of rows) {
      const cat = row.category || "features";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push({
        id: Number(row.id),
        title: row.title,
        summary: row.summary,
        category: cat,
        voteCount: row.vote_count,
      });
    }
    res.status(200).json({ categories: CATEGORY_ORDER, labels: CATEGORY_LABELS, proposals: grouped });
  } catch (e) {
    console.error("proposals list failed:", e && e.message);
    res.status(502).json({ error: "list failed" });
  }
}
