// /api/maintenance — site-maintenance flags (monitor → admin pipeline).
//
// POST  (monitors): create/refresh a flag. Auth: x-maintenance-token header
//        matching MAINTENANCE_TOKEN (or CRON_SECRET as fallback), OR the
//        admin bearer. Body: { source, title, detail?, severity?, url?,
//        dedupeKey? }. Upserts on dedupeKey; a recurrence of a resolved
//        flag reopens it (the "didn't hold" signal).
// GET   (admin):    ?status=open|acked|resolved (empty = all).
// PATCH (admin):    { ids: [..], status: 'open'|'acked'|'resolved' }.
import {
  cors,
  authorizeAdmin,
  ensureSchema,
  readJsonBody,
  str,
  upsertMaintenanceFlag,
  listMaintenanceFlags,
  setMaintenanceStatus,
} from "./_supa.js";
import { authorizeMonitor } from "./_auth.js";

const SEVERITIES = new Set(["critical", "warning", "info"]);
const STATUSES = new Set(["open", "acked", "resolved"]);

export default async function handler(req, res) {
  cors(res, "GET, POST, PATCH, OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, x-maintenance-token"
  );
  if (req.method === "OPTIONS") return res.status(204).end();

  try {
    if (req.method === "POST") {
      if (!authorizeMonitor(req) && !authorizeAdmin(req)) {
        return res.status(401).json({ error: "unauthorized" });
      }
      const b = await readJsonBody(req);
      const source = str(b.source, 60);
      const title = str(b.title, 300);
      if (!source || !title) {
        return res.status(400).json({ error: "source and title required" });
      }
      const severity = SEVERITIES.has(b.severity) ? b.severity : "warning";
      await ensureSchema();
      const row = await upsertMaintenanceFlag({
        dedupe_key: str(b.dedupeKey, 200),
        source,
        severity,
        title,
        detail: str(b.detail, 4000),
        url: str(b.url, 500),
      });
      return res.status(200).json({
        id: Number(row.id),
        status: row.status,
        seenCount: Number(row.seen_count),
      });
    }

    if (!authorizeAdmin(req)) {
      return res.status(401).json({ error: "unauthorized" });
    }

    if (req.method === "GET") {
      await ensureSchema();
      const statusRaw = str(req.query?.status, 20) || "";
      const rows = await listMaintenanceFlags(
        STATUSES.has(statusRaw) ? statusRaw : null
      );
      return res.status(200).json({
        flags: rows.map((r) => ({
          id: Number(r.id),
          createdAt: r.created_at,
          lastSeen: r.last_seen,
          seenCount: Number(r.seen_count),
          source: r.source,
          severity: r.severity,
          title: r.title,
          detail: r.detail,
          url: r.url,
          status: r.status,
          resolvedAt: r.resolved_at,
        })),
      });
    }

    if (req.method === "PATCH") {
      const b = await readJsonBody(req);
      const ids = (Array.isArray(b.ids) ? b.ids : [])
        .map(Number)
        .filter((n) => Number.isFinite(n) && n > 0);
      if (!ids.length || !STATUSES.has(b.status)) {
        return res.status(400).json({ error: "ids and valid status required" });
      }
      await ensureSchema();
      await setMaintenanceStatus(ids, b.status);
      return res.status(200).json({ updated: ids.length });
    }

    return res.status(405).json({ error: "method not allowed" });
  } catch (e) {
    console.error("maintenance failed:", e && e.message);
    return res.status(502).json({ error: "maintenance failed" });
  }
}
