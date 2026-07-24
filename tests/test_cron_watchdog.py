"""Regression tests for the Vercel cron watchdog authorization gate."""

from __future__ import annotations

import json
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRON = ROOT / "api" / "cron-watchdog.js"


class CronWatchdogAuthTest(unittest.TestCase):
    def test_missing_or_wrong_cron_secret_fails_before_network(self):
        script = textwrap.dedent(
            f"""
            import assert from "node:assert/strict";
            import fs from "node:fs";
            import vm from "node:vm";

            let fetchCalled = false;
            const source = fs.readFileSync({json.dumps(str(CRON))}, "utf8")
              .replace(
                'import {{ upsertMaintenanceFlag }} from "./_supa.js";',
                'const upsertMaintenanceFlag = async () => {{}};'
              )
              .replace(
                "export default async function handler",
                "async function handler"
              ) + "\\nglobalThis.__handler = handler;\\n";

            const context = {{
              console,
              process: {{ env: {{ GITHUB_TOKEN: "token" }} }},
              fetch: async () => {{
                fetchCalled = true;
                throw new Error("fetch should not be called before auth passes");
              }},
            }};
            vm.createContext(context);
            vm.runInContext(source, context);

            function res() {{
              return {{
                statusCode: null,
                body: null,
                headers: {{}},
                setHeader(k, v) {{ this.headers[k] = v; return this; }},
                status(code) {{ this.statusCode = code; return this; }},
                json(body) {{ this.body = body; return this; }},
                end() {{ this.ended = true; return this; }},
              }};
            }}

            const missingSecretRes = res();
            await context.__handler({{ method: "GET", headers: {{}} }}, missingSecretRes);
            assert.equal(missingSecretRes.statusCode, 401);
            assert.equal(fetchCalled, false);

            context.process.env.CRON_SECRET = "expected";
            const wrongSecretRes = res();
            await context.__handler(
              {{ method: "GET", headers: {{ authorization: "Bearer wrong" }} }},
              wrongSecretRes
            );
            assert.equal(wrongSecretRes.statusCode, 401);
            assert.equal(fetchCalled, false);
            """
        )
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)


if __name__ == "__main__":
    unittest.main()
