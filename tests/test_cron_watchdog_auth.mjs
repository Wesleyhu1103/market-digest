// Auth tests for /api/cron-watchdog's fail-closed bearer check
// (api/_auth.js authorizeCronBearer) and the real handler wiring.
//
// Run with:  node tests/test_cron_watchdog_auth.mjs
//
// Part 1 needs no dependencies (api/_auth.js is dep-free by design).
// Part 2 imports the real handler, which pulls the `postgres` package —
// run `npm install` first; without it Part 2 is skipped loudly. DB env vars
// are cleared and global fetch is stubbed with a recorder that throws, so:
//   401/503 with zero recorded fetches proves rejection happened before any
//   network work; 502 "index fetch" with one recorded fetch proves the
//   request cleared auth and reached the handler's real work.

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

// ── Part 1: pure credential matrix ─────────────────────────────────────
const { authorizeCronBearer } = await import("../api/_auth.js");

process.env.CRON_SECRET = "cron-token";

check("cron: exact bearer accepted", () =>
  assert.equal(authorizeCronBearer(req({ authorization: "Bearer cron-token" })), true));
check("cron: wrong bearer rejected", () =>
  assert.equal(authorizeCronBearer(req({ authorization: "Bearer nope" })), false));
check("cron: missing header rejected", () =>
  assert.equal(authorizeCronBearer(req({})), false));
check("cron: token without Bearer prefix rejected", () =>
  assert.equal(authorizeCronBearer(req({ authorization: "cron-token" })), false));

delete process.env.CRON_SECRET;
check("cron: fails closed when secret unconfigured", () =>
  assert.equal(authorizeCronBearer(req({ authorization: "Bearer cron-token" })), false));
check("cron: empty bearer does not match unset secret", () =>
  assert.equal(authorizeCronBearer(req({ authorization: "Bearer " })), false));

// ── Part 2: real handler wiring (405 → 503 → 401 → work order) ─────────
// Clear DB config BEFORE importing the handler chain: _supa.js reads the
// env at module load. safeFlag() must swallow the resulting DB error.
delete process.env.SUPABASE_DB_URL;
delete process.env.POSTGRES_URL;
delete process.env.DATABASE_URL;

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

const RealDate = globalThis.Date;
async function withFakeNow(iso, fn) {
  class FakeDate extends RealDate {
    constructor(...args) {
      if (args.length) super(...args);
      else super(iso);
    }
    static now() {
      return new RealDate(iso).getTime();
    }
  }
  FakeDate.UTC = RealDate.UTC;
  FakeDate.parse = RealDate.parse;
  globalThis.Date = FakeDate;
  try {
    return await fn();
  } finally {
    globalThis.Date = RealDate;
  }
}

let handler = null;
try {
  ({ default: handler } = await import("../api/cron-watchdog.js"));
} catch (e) {
  if (e.code === "ERR_MODULE_NOT_FOUND") {
    console.log("\nSKIP  handler wiring tests: `postgres` not installed (run npm install)");
  } else {
    throw e;
  }
}

if (handler) {
  const fetchCalls = [];
  globalThis.fetch = async (url) => {
    fetchCalls.push(String(url));
    throw new Error("network disabled in tests");
  };

  const call = async (r) => {
    const { res, out } = fakeRes();
    fetchCalls.length = 0;
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
  const staleIndexBody = "<h1>Monday, August 10, 2026</h1><script>date: '2026-08-10'</script>";
  const setInProgressFetch = (calls) => {
    globalThis.fetch = async (url) => {
      const u = String(url);
      calls.push(u);
      if (u.includes("/docs/index.html")) {
        return { ok: true, text: async () => staleIndexBody };
      }
      if (u.includes("/actions/workflows/publish-digest.yml/runs")) {
        return { ok: true, json: async () => ({ total_count: 1 }) };
      }
      throw new Error(`unexpected fetch ${u}`);
    };
  };

  await acheck("handler: bad method -> 405", async () => {
    const out = await call(req({}, { method: "DELETE" }));
    assert.equal(out.statusCode, 405);
    assert.equal(fetchCalls.length, 0);
  });

  delete process.env.CRON_SECRET;
  await acheck("handler: secret unset -> 503, no network", async () => {
    const out = await call(req({}, { method: "GET" }));
    assert.equal(out.statusCode, 503);
    assert.match(out.body.error, /CRON_SECRET/);
    assert.equal(fetchCalls.length, 0);
  });
  await acheck("handler: secret unset -> 503 even with a bearer", async () => {
    const out = await call(
      req({ authorization: "Bearer anything" }, { method: "GET" })
    );
    assert.equal(out.statusCode, 503);
    assert.equal(fetchCalls.length, 0);
  });

  process.env.CRON_SECRET = "cron-token";
  await acheck("handler: no bearer -> 401, no network", async () => {
    const out = await call(req({}, { method: "GET" }));
    assert.equal(out.statusCode, 401);
    assert.equal(fetchCalls.length, 0);
  });
  await acheck("handler: wrong bearer -> 401, no network", async () => {
    const out = await call(req({ authorization: "Bearer nope" }, { method: "GET" }));
    assert.equal(out.statusCode, 401);
    assert.equal(fetchCalls.length, 0);
  });
  await acheck("handler: correct bearer clears auth, reaches index fetch (502 here)", async () => {
    const out = await call(
      req({ authorization: "Bearer cron-token" }, { method: "POST" })
    );
    assert.equal(out.statusCode, 502);
    assert.equal(fetchCalls.length, 1);
    assert.match(fetchCalls[0], /docs\/index\.html/);
  });

  process.env.GITHUB_TOKEN = "gh-token";
  await acheck("handler: stale + in-progress before alarm -> 200 skip", async () => {
    const calls = [];
    setInProgressFetch(calls);
    const out = await withFakeNow("2026-08-11T12:00:00Z", () =>
      call(req({ authorization: "Bearer cron-token" }, { method: "GET" }))
    );
    assert.equal(out.statusCode, 200);
    assert.equal(out.body.action, "skip_in_progress");
    assert.equal(calls.length, 2);
    assert.ok(!calls.some((u) => u.includes("/dispatches")));
  });

  await acheck("handler: stale + in-progress past alarm -> 503", async () => {
    const calls = [];
    setInProgressFetch(calls);
    const out = await withFakeNow("2026-08-11T14:00:00Z", () =>
      call(req({ authorization: "Bearer cron-token" }, { method: "GET" }))
    );
    assert.equal(out.statusCode, 503);
    assert.equal(out.body.action, "stale_in_progress");
    assert.match(out.body.error, /in progress/);
    assert.equal(calls.length, 2);
    assert.ok(!calls.some((u) => u.includes("/dispatches")));
  });
  delete process.env.GITHUB_TOKEN;
}

if (failures) {
  console.error(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log("\nall cron-watchdog auth tests passed");
