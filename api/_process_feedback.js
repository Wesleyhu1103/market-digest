// Cluster unprocessed reader feedback into pending proposals.
import {
  ensureSchema,
  listUnprocessedFeedback,
  insertProposal,
  markFeedbackProcessed,
} from "./_supa.js";

const MIN_LEN = 15;
const JACCARD_THRESHOLD = 0.55;

const CATEGORY_RULES = [
  ["coverage", /\b(miss(ed|ing)?|cover(age)?|story|stories|topic|event|earnings|ticker)\b/i],
  ["depth", /\b(deep(er|th)?|detail|long(er|er)?|shorter|skim|verbose|summary|brief)\b/i],
  ["format", /\b(format|layout|design|ui|ux|mobile|chart|graph|visual|font|readability|nav)\b/i],
  ["sources", /\b(source|outlet|wsj|bloomberg|economist|nyt|cnbc|ft|atlantic|rss|feed)\b/i],
  ["sections", /\b(section|add a|new column|ondeck|quiz|verdict|narrative|archive)\b/i],
];

function extractText(row) {
  const text = [row.missing, row.open]
    .filter(Boolean)
    .map((p) => String(p).trim())
    .join(" ")
    .trim();
  if (text.length < MIN_LEN) return null;
  if (!/[a-zA-Z]/.test(text)) return null;
  return text;
}

function normalize(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function wordSet(text) {
  return new Set(normalize(text).split(/\s+/).filter((w) => w.length > 2));
}

function jaccard(a, b) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  for (const w of a) if (b.has(w)) inter++;
  const union = a.size + b.size - inter;
  return union ? inter / union : 0;
}

function categorize(text) {
  for (const [cat, pat] of CATEGORY_RULES) {
    if (pat.test(text)) return cat;
  }
  return "features";
}

function titleFromText(text) {
  const t = text.trim();
  if (t.length <= 72) return t ? t[0].toUpperCase() + t.slice(1) : t;
  let cut = t.slice(0, 72);
  const sp = cut.lastIndexOf(" ");
  if (sp > 0) cut = cut.slice(0, sp);
  return cut[0].toUpperCase() + cut.slice(1) + "…";
}

function summaryFromCluster(texts) {
  if (texts.length === 1) return texts[0].slice(0, 240);
  const lead = texts[0].slice(0, 160);
  return `${texts.length} readers suggested similar changes: ${lead}${texts[0].length > 160 ? "…" : ""}`;
}

function clusterItems(items) {
  const clusters = [];
  for (const item of items) {
    const words = wordSet(item.text);
    let placed = false;
    for (const cluster of clusters) {
      if (jaccard(words, cluster.words) >= JACCARD_THRESHOLD) {
        cluster.items.push(item);
        for (const w of words) cluster.words.add(w);
        placed = true;
        break;
      }
    }
    if (!placed) clusters.push({ words, items: [item] });
  }
  return clusters;
}

export async function processFeedback() {
  await ensureSchema();
  const rows = await listUnprocessedFeedback();
  if (!rows.length) {
    return { created: 0, processed: 0, skipped: 0, proposals: [], message: "No unprocessed feedback." };
  }

  const seenNorm = new Set();
  const valid = [];
  let skipped = 0;

  for (const row of rows) {
    const text = extractText(row);
    if (!text) {
      skipped++;
      continue;
    }
    const norm = normalize(text);
    if (seenNorm.has(norm)) {
      skipped++;
      continue;
    }
    seenNorm.add(norm);
    valid.push({ id: row.id, text, categoryHint: categorize(text) });
  }

  const allIds = rows.map((r) => r.id);
  const processedIds = [];
  const proposals = [];

  if (!valid.length) {
    await markFeedbackProcessed(allIds);
    return {
      created: 0,
      processed: allIds.length,
      skipped,
      proposals: [],
      message: `Nothing valid to cluster (${skipped} too short or duplicate). Marked ${allIds.length} row(s) processed.`,
    };
  }

  const clusters = clusterItems(valid);
  for (const cluster of clusters) {
    const texts = cluster.items.map((i) => i.text);
    const ids = cluster.items.map((i) => i.id);
    processedIds.push(...ids);
    const cats = cluster.items.map((i) => i.categoryHint);
    const category = cluster.items.reduce((best, item) => {
      const count = cats.filter((c) => c === item.categoryHint).length;
      const bestCount = cats.filter((c) => c === best).length;
      return count > bestCount ? item.categoryHint : best;
    }, cluster.items[0].categoryHint);
    const id = await insertProposal({
      title: titleFromText(texts[0]),
      summary: summaryFromCluster(texts),
      category,
      status: "pending",
      source_feedback_ids: ids,
    });
    proposals.push({ id, category, title: titleFromText(texts[0]), sources: ids.length });
  }

  const unclustered = allIds.filter((id) => !processedIds.includes(id));
  await markFeedbackProcessed([...processedIds, ...unclustered]);

  return {
    created: proposals.length,
    processed: allIds.length,
    skipped,
    proposals,
    message: `Created ${proposals.length} pending proposal(s); marked ${allIds.length} feedback row(s) processed.`,
  };
}
