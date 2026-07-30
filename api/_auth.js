// Request-auth helpers shared by the admin/monitor endpoints.
//
// Two credential classes exist on this API:
//
//  - Admin bearer (FEEDBACK_ADMIN_SECRET): the human credential the admin
//    page prompts for. Full access to the admin endpoints.
//  - Monitor token (MAINTENANCE_TOKEN, CRON_SECRET fallback): the automation
//    credential GitHub workflows already hold — and provably share with this
//    deployment — for posting maintenance flags (x-maintenance-token header).
//
// The monitor token is also accepted, narrowly scoped, on /api/admin-proposals
// (see monitorMayProposals) so the feedback pipeline does not require a second
// hand-synced copy of the admin bearer as a repo secret: process-feedback ran
// red for weeks waiting on a FEEDBACK_ADMIN_SECRET repo secret that never got
// added, while the same runs successfully posted flags with MAINTENANCE_TOKEN.
//
// Kept dependency-free (no _supa import) so tests can exercise the auth and
// scope rules without installing the API's node deps.

export function authorizeAdmin(req) {
  const secret = process.env.FEEDBACK_ADMIN_SECRET;
  if (!secret) return false;
  const auth = req.headers.authorization || "";
  return auth === `Bearer ${secret}`;
}

export function authorizeMonitor(req) {
  const token = process.env.MAINTENANCE_TOKEN || process.env.CRON_SECRET;
  if (!token) return false;
  return (req.headers["x-maintenance-token"] || "") === token;
}

// The exact two operations the process-feedback workflow performs, and
// nothing else: clustering is idempotent, and the pending list is the same
// content the pipeline publishes into the public review issue. Approve,
// reject, other status filters, and raw feedback stay admin-bearer-only.
export function monitorMayProposals(method, { status, action } = {}) {
  if (method === "GET") return status === "pending";
  if (method === "POST") return action === "process";
  return false;
}
