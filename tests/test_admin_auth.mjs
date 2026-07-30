// Auth + scope tests for the two-tier admin API credentials (api/_auth.js)
// and the real /api/admin-proposals handler wiring.
//
// Run with:  node tests/test_admin_auth.mjs
//
// Part 1 needs no dependencies (api/_auth.js is dep-free by design).
// Part 2 imports the real handler, which pulls the `postgres` package —
// run `npm install` first; without it Part 2 is skipped loudly. DB env vars
// are cleared, so any path that survives auth+scope must end 502 ("admin
// failed", thrown by the missing SUPABASE_DB_URL) — that 502 is the proof
// a request cleared the auth layer, while 401/403 prove it never touched
// the DB layer at all.

import assert from "node:assert/strict";

let failures = 0;
function check(name, fn) {
  try {
    fn();
    console.log(`  ok  ${name}`);
  } catch (e) {
    failures++;
    console.error(`FAIL  ${name}\n      ${e.message}`);
  }
}

const req = (headers = {}, extra = {}) => ({ headers, ...extra });

// ── Part 1: pure credential + scope matrix ─────────────────────────────
const { authorizeAdmin, authorizeMonitor, monitorMayProposals } = await import(
  "../api/_auth.js"
);

process.env.FEEDBACK_ADMIN_SECRET = "adm-secret";
process.env.MAINTENANCE_TOKEN = "mon-token";
process.env.CRON_SECRET = "cron-token";

check("admin: exact bearer accepted", () =>
  assert.equal(authorizeAdmin(req({ authorization: "Bearer adm-secret" })), true));
check("admin: wrong bearer rejected", () =>
  assert.equal(authorizeAdmin(req({ authorization: "Bearer nope" })), false));
check("admin: missing header rejected", () =>
  assert.equal(authorizeAdmin(req({})), false));
check("monitor: MAINTENANCE_TOKEN accepted", () =>
  assert.equal(authorizeMonitor(req({ "x-maintenance-token": "mon-token" })), true));
check("monitor: wrong token rejected", () =>
  assert.equal(authorizeMonitor(req({ "x-maintenance-token": "nope" })), false));
check("monitor: admin bearer is not a monitor token", () =>
  assert.equal(authorizeMonitor(req({ authorization: "Bearer adm-secret" })), false));

delete process.env.MAINTENANCE_TOKEN;
check("monitor: CRON_SECRET fallback when MAINTENANCE_TOKEN unset", () =>
  assert.equal(authorizeMonitor(req({ "x-maintenance-token": "cron-token" })), true));
delete process.env.CRON_SECRET;
check("monitor: fails closed when no token configured", () =>
  assert.equal(authorizeMonitor(req({ "x-maintenance-token": "" })), false));
delete process.env.FEEDBACK_ADMIN_SECRET;
check("admin: fails closed when secret unconfigured", () =>
  assert.equal(authorizeAdmin(req({ authorization: "Bearer adm-secret" })), false));

check("scope: GET pending allowed", () =>
  assert.equal(monitorMayProposals("GET", { status: "pending" }), true));
check("scope: GET approved denied", () =>
  assert.equal(monitorMayProposals("GET", { status: "approved" }), false));
check("scope: GET without status denied", () =>
  assert.equal(monitorMayProposals("GET", { status: null }), false));
check("scope: POST process allowed", () =>
  assert.equal(monitorMayProposals("POST", { action: "process" }), true));
check("scope: POST approve denied", () =>
  assert.equal(monitorMayProposals("POST", { action: "approve" }), false));
check("scope: POST reject denied", () =>
  assert.equal(monitorMayProposals("POST", { action: "reject" }), false));
check("scope: POST without action denied", () =>
  assert.equal(monitorMayProposals("POST", {}), false));
check("scope: other methods denied", () =>
  assert.equal(monitorMayProposals("PATCH", { status: "pending" }), false));

// ── Part 2: real handler wiring (401 → 403 → DB order) ─────────────────
// Clear DB config BEFORE importing the handler chain: _supa.js reads the
// env at module load.
delete process.env.SUPABASE_DB_URL;
delete process.env.POSTGRES_URL;
delete process.env.DATABASE_URL;
process.env.FEEDBACK_ADMIN_SECRET = "adm-secret";
process.env.MAINTENANCE_TOKEN = "mon-token";

function fakeRes() {
  const out = { statusCode: null, body: null, headers: {} };
  const res = {
    setHeader: (k, v) => (out.headers[k] = v),
    status(c) {
      out.statusCode = c;
      return res;
    },
    json(b) {
      out.body = b;
      return res;
    },
    end() {
      return res;
    },
  };
  return { res, out };
}

let handler = null;
try {
  ({ default: handler } = await import("../api/admin-proposals.js"));
} catch (e) {
  if (e.code === "ERR_MODULE_NOT_FOUND") {
    console.log("\nSKIP  handler wiring tests: `postgres` not installed (run npm install)");
  } else {
    throw e;
  }
}

if (handler) {
  const call = async (r) => {
    const { res, out } = fakeRes();
    await handler(r, res);
    return out;
  };
  const acheck = async (name, fn) => {
    try {
      await fn();
      console.log(`  ok  ${name}`);
    } catch (e) {
      failures++;
      console.error(`FAIL  ${name}\n      ${e.message}`);
    }
  };

  await acheck("handler: no credentials -> 401", async () => {
    const out = await call(req({}, { method: "GET", query: { status: "pending" } }));
    assert.equal(out.statusCode, 401);
  });
  await acheck("handler: wrong bearer -> 401", async () => {
    const out = await call(
      req({ authorization: "Bearer nope" }, { method: "GET", query: { status: "pending" } })
    );
    assert.equal(out.statusCode, 401);
  });
  await acheck("handler: monitor GET non-pending -> 403 before DB", async () => {
    const out = await call(
      req({ "x-maintenance-token": "mon-token" }, { method: "GET", query: { status: "approved" } })
    );
    assert.equal(out.statusCode, 403);
    assert.match(out.body.error, /status=pending/);
  });
  await acheck("handler: monitor GET without status -> 403 before DB", async () => {
    const out = await call(
      req({ "x-maintenance-token": "mon-token" }, { method: "GET", query: {} })
    );
    assert.equal(out.statusCode, 403);
  });
  await acheck("handler: monitor POST approve -> 403 before DB", async () => {
    const out = await call(
      req(
        { "x-maintenance-token": "mon-token" },
        { method: "POST", body: { action: "approve", ids: [1] } }
      )
    );
    assert.equal(out.statusCode, 403);
    assert.match(out.body.error, /process/);
  });
  await acheck("handler: monitor POST process passes scope, reaches DB (502 here)", async () => {
    const out = await call(
      req({ "x-maintenance-token": "mon-token" }, { method: "POST", body: { action: "process" } })
    );
    assert.equal(out.statusCode, 502);
  });
  await acheck("handler: monitor GET pending passes scope, reaches DB (502 here)", async () => {
    const out = await call(
      req({ "x-maintenance-token": "mon-token" }, { method: "GET", query: { status: "pending" } })
    );
    assert.equal(out.statusCode, 502);
  });
  await acheck("handler: admin GET any status unrestricted, reaches DB (502 here)", async () => {
    const out = await call(
      req({ authorization: "Bearer adm-secret" }, { method: "GET", query: { status: "approved" } })
    );
    assert.equal(out.statusCode, 502);
  });
  await acheck("handler: admin POST approve unrestricted, reaches DB (502 here)", async () => {
    const out = await call(
      req(
        { authorization: "Bearer adm-secret" },
        { method: "POST", body: { action: "approve", ids: [1] } }
      )
    );
    assert.equal(out.statusCode, 502);
  });
  await acheck("handler: OPTIONS preflight needs no auth -> 204", async () => {
    const out = await call(req({}, { method: "OPTIONS" }));
    assert.equal(out.statusCode, 204);
  });
}

if (failures) {
  console.error(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log("\nall auth tests passed");
