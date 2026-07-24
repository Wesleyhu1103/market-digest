import json
import os
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_node(script: str, env_updates: dict[str, str | None] | None = None) -> dict:
    env = os.environ.copy()
    for key in ("CRON_SECRET", "GITHUB_TOKEN"):
        env.pop(key, None)
    for key, value in (env_updates or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout.strip().splitlines()[-1])


HANDLER_HARNESS = textwrap.dedent(
    """
    import handler from './api/cron-watchdog.js';

    let fetchCalled = false;
    globalThis.fetch = async () => {
      fetchCalled = true;
      return {
        ok: true,
        text: async () => "<html><script>date: '2999-01-01'</script><h1>Friday, July 24, 2026</h1></html>"
      };
    };

    const req = { method: 'GET', headers: HEADERS };
    const res = {
      statusCode: null,
      body: null,
      status(code) { this.statusCode = code; return this; },
      json(obj) { this.body = obj; return this; },
      end() { this.ended = true; return this; }
    };

    await handler(req, res);
    console.log(JSON.stringify({ status: res.statusCode, body: res.body, fetchCalled }));
    """
)


class CronWatchdogAuthTests(unittest.TestCase):
    def test_missing_cron_secret_fails_closed_before_fetch(self):
        out = run_node(HANDLER_HARNESS.replace("HEADERS", "{}"))

        self.assertEqual(out["status"], 401)
        self.assertEqual(out["body"]["error"], "unauthorized")
        self.assertFalse(out["fetchCalled"])

    def test_mismatched_cron_secret_fails_before_fetch(self):
        out = run_node(
            HANDLER_HARNESS.replace("HEADERS", "{ authorization: 'Bearer wrong' }"),
            {"CRON_SECRET": "expected"},
        )

        self.assertEqual(out["status"], 401)
        self.assertFalse(out["fetchCalled"])

    def test_matching_cron_secret_allows_freshness_check(self):
        out = run_node(
            HANDLER_HARNESS.replace("HEADERS", "{ authorization: 'Bearer expected' }"),
            {"CRON_SECRET": "expected"},
        )

        self.assertEqual(out["status"], 200)
        self.assertTrue(out["fetchCalled"])
        self.assertEqual(out["body"]["action"], "skip")


if __name__ == "__main__":
    unittest.main()
