"""Regression tests for the Vercel cron watchdog auth boundary.

The handler imports the Supabase helper at module load time, but these tests
only need the request/auth/fetch path.  A temporary copy stubs that import so
the Node process can run without a database driver or real network access.
"""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDLER = ROOT / "api" / "cron-watchdog.js"


def run_node_watchdog(tmp_path, body: str):
    source = HANDLER.read_text()
    source = source.replace(
        'import { upsertMaintenanceFlag } from "./_supa.js";',
        "async function upsertMaintenanceFlag(flag) { globalThis.__flags.push(flag); }",
    )
    module = tmp_path / "cron-watchdog-under-test.mjs"
    module.write_text(source)

    script = tmp_path / "run-watchdog.mjs"
    script.write_text(
        textwrap.dedent(
            f"""
            import handler from {json.dumps(module.as_uri())};
            globalThis.__flags = [];
            {body}
            """
        )
    )
    return subprocess.run(
        ["node", str(script)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env={"PATH": os.environ.get("PATH", "")},
    )


def test_missing_cron_secret_rejects_before_network_or_flags(tmp_path):
    proc = run_node_watchdog(
        tmp_path,
        """
        delete process.env.CRON_SECRET;
        process.env.GITHUB_TOKEN = "configured-actions-token";
        let fetches = 0;
        globalThis.fetch = async () => {
          fetches += 1;
          throw new Error("fetch must not run before auth");
        };
        const res = {
          statusCode: null,
          payload: null,
          status(code) { this.statusCode = code; return this; },
          json(payload) { this.payload = payload; },
        };
        await handler({ method: "GET", headers: {} }, res);
        console.log(JSON.stringify({
          statusCode: res.statusCode,
          payload: res.payload,
          fetches,
          flags: globalThis.__flags.length,
        }));
        """,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result == {
        "statusCode": 401,
        "payload": {"error": "unauthorized"},
        "fetches": 0,
        "flags": 0,
    }


def test_matching_cron_secret_allows_current_digest_check(tmp_path):
    proc = run_node_watchdog(
        tmp_path,
        """
        process.env.CRON_SECRET = "cron-secret";
        delete process.env.GITHUB_TOKEN;
        const parts = new Intl.DateTimeFormat("en-CA", {
          timeZone: "America/New_York",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        }).formatToParts(new Date());
        const today = `${parts.find((p) => p.type === "year").value}-${parts.find((p) => p.type === "month").value}-${parts.find((p) => p.type === "day").value}`;
        let fetches = 0;
        globalThis.fetch = async () => {
          fetches += 1;
          return { ok: true, text: async () => `date: '${today}'` };
        };
        const res = {
          statusCode: null,
          payload: null,
          status(code) { this.statusCode = code; return this; },
          json(payload) { this.payload = payload; },
        };
        await handler(
          { method: "GET", headers: { authorization: "Bearer cron-secret" } },
          res
        );
        console.log(JSON.stringify({
          statusCode: res.statusCode,
          action: res.payload.action,
          stale: res.payload.stale,
          fetches,
        }));
        """,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == {
        "statusCode": 200,
        "action": "skip",
        "stale": False,
        "fetches": 1,
    }
