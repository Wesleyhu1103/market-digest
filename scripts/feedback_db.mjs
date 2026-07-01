#!/usr/bin/env node
/** CLI bridge for Python feedback scripts — uses api/_supa.js Postgres helpers. */
import {
  ensureSchema,
  listUnprocessedFeedback,
  insertProposal,
  markFeedbackProcessed,
  listProposalsAdmin,
  getFeedbackByIds,
  listRawFeedback,
  updateProposalStatus,
  getTopVotedProposals,
} from "../api/_supa.js";

const cmd = process.argv[2];

async function main() {
  await ensureSchema();

  if (cmd === "unprocessed") {
    const rows = await listUnprocessedFeedback();
    console.log(JSON.stringify(rows));
    return;
  }

  if (cmd === "insert-proposal") {
    const payload = JSON.parse(await readStdin());
    const id = await insertProposal(payload);
    console.log(JSON.stringify({ id }));
    return;
  }

  if (cmd === "mark-processed") {
    const ids = JSON.parse(await readStdin());
    await markFeedbackProcessed(ids);
    console.log(JSON.stringify({ ok: true }));
    return;
  }

  if (cmd === "list-proposals") {
    const status = process.argv[3] || null;
    const rows = await listProposalsAdmin(status);
    const allIds = [...new Set(rows.flatMap((p) => p.source_feedback_ids || []))];
    const feedback = allIds.length ? await getFeedbackByIds(allIds) : [];
    const byId = Object.fromEntries(feedback.map((f) => [Number(f.id), f]));
    const out = rows.map((p) => ({
      id: Number(p.id),
      title: p.title,
      summary: p.summary,
      category: p.category,
      status: p.status,
      vote_count: p.vote_count,
      reject_reason: p.reject_reason,
      created_at: p.created_at,
      source_feedback_ids: p.source_feedback_ids || [],
      sources: (p.source_feedback_ids || []).map((fid) => {
        const f = byId[Number(fid)];
        if (!f) return { id: fid, text: "(missing)", date: null };
        const text = [f.missing, f.open].filter(Boolean).join(" | ").trim();
        return { id: Number(f.id), text, date: f.digest_date || f.created_at };
      }),
    }));
    console.log(JSON.stringify(out));
    return;
  }

  if (cmd === "raw") {
    const days = process.argv[3] ? Number(process.argv[3]) : null;
    const rows = await listRawFeedback(days);
    console.log(JSON.stringify(rows));
    return;
  }

  if (cmd === "approve") {
    const ids = process.argv.slice(3).map(Number).filter((n) => n > 0);
    await updateProposalStatus(ids, "approved");
    console.log(JSON.stringify({ ok: true, approved: ids }));
    return;
  }

  if (cmd === "reject") {
    const reasonIdx = process.argv.indexOf("--reason");
    const reason = reasonIdx >= 0 ? process.argv[reasonIdx + 1] : null;
    const ids = process.argv.slice(3).filter((a) => a !== "--reason" && a !== reason).map(Number).filter((n) => n > 0);
    await updateProposalStatus(ids, "rejected", reason);
    console.log(JSON.stringify({ ok: true, rejected: ids }));
    return;
  }

  if (cmd === "top-voted") {
    const limit = Number(process.argv[3] || 10);
    const rows = await getTopVotedProposals(limit);
    console.log(JSON.stringify(rows));
    return;
  }

  console.error(`Unknown command: ${cmd}`);
  process.exit(1);
}

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (data += c));
    process.stdin.on("end", () => resolve(data || "{}"));
  });
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
