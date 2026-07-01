// POST /api/proposals-vote — upvote or remove vote on an approved proposal.
// Body: { proposalId, action: "upvote" | "remove", voterId? }
import {
  cors,
  readJsonBody,
  ensureSchema,
  castProposalVote,
  voterHashFromRequest,
} from "./_supa.js";

export default async function handler(req, res) {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method not allowed" });

  const b = (await readJsonBody(req)) || {};
  const proposalId = b.proposalId;
  const action = b.action === "remove" ? "remove" : "upvote";
  const voterHash = voterHashFromRequest(req, b.voterId);

  try {
    await ensureSchema();
    const result = await castProposalVote(proposalId, voterHash, action);
    res.status(200).json(result);
  } catch (e) {
    const msg = (e && e.message) || "vote failed";
    if (msg.includes("not found")) return res.status(404).json({ error: msg });
    console.error("proposal vote failed:", msg);
    res.status(502).json({ error: "vote failed" });
  }
}
