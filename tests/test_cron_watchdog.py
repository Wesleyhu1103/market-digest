import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT = Path(__file__).resolve().parents[1] / "api" / "cron-watchdog.js"


def current_digest_h1():
    today = datetime.now(ZoneInfo("America/New_York"))
    return today.strftime("%A, %B %d, %Y")


def run_handler(env, headers=None, html=None):
    source = SCRIPT.read_text()
    source = source.replace(
        'import { upsertMaintenanceFlag } from "./_supa.js";',
        "async function upsertMaintenanceFlag() {}",
    )
    source = source.replace(
        "export default async function handler(req, res) {",
        "async function handler(req, res) {",
    )
    html = html or f"<html><body><h1>{current_digest_h1()}</h1></body></html>"
    runner = textwrap.dedent(
        f"""
        {source}

        let fetchCalls = 0;
        global.fetch = async () => {{
          fetchCalls += 1;
          return {{
            ok: true,
            status: 200,
            text: async () => {json.dumps(html)},
            json: async () => ({{ total_count: 0 }}),
          }};
        }};

        const res = {{
          statusCode: 200,
          body: null,
          status(code) {{ this.statusCode = code; return this; }},
          json(body) {{ this.body = body; }},
        }};

        await handler({{
          method: "GET",
          headers: {json.dumps(headers or {})},
        }}, res);
        console.log(JSON.stringify({{
          statusCode: res.statusCode,
          body: res.body,
          fetchCalls,
        }}));
        """
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
        f.write(runner)
        runner_path = f.name
    try:
        proc = subprocess.run(
            ["node", runner_path],
            capture_output=True,
            text=True,
            env={"PATH": os.environ.get("PATH", ""), **env},
            cwd=str(SCRIPT.parents[1]),
        )
    finally:
        os.unlink(runner_path)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout.strip().splitlines()[-1])


class CronWatchdogAuthTests(unittest.TestCase):
    def test_missing_cron_secret_rejects_before_fetch(self):
        result = run_handler({"GITHUB_TOKEN": "token"})

        self.assertEqual(result["statusCode"], 401)
        self.assertEqual(result["body"], {"error": "unauthorized"})
        self.assertEqual(result["fetchCalls"], 0)

    def test_wrong_bearer_rejects_before_fetch(self):
        result = run_handler(
            {"CRON_SECRET": "expected", "GITHUB_TOKEN": "token"},
            headers={"authorization": "Bearer wrong"},
        )

        self.assertEqual(result["statusCode"], 401)
        self.assertEqual(result["body"], {"error": "unauthorized"})
        self.assertEqual(result["fetchCalls"], 0)

    def test_matching_bearer_allows_current_digest_check(self):
        result = run_handler(
            {"CRON_SECRET": "expected", "GITHUB_TOKEN": "token"},
            headers={"authorization": "Bearer expected"},
        )

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["body"]["action"], "skip")
        self.assertFalse(result["body"]["stale"])
        self.assertEqual(result["fetchCalls"], 1)


if __name__ == "__main__":
    unittest.main()
