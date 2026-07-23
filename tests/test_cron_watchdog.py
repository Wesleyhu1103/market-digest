import json
import os
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cron_watchdog(auth_header="", cron_secret=None):
    script = textwrap.dedent(
        f"""
        import handler from './api/cron-watchdog.js';

        let fetchCalls = 0;
        globalThis.fetch = async () => {{
          fetchCalls += 1;
          throw new Error('fetch should not be called before authorization');
        }};

        const req = {{
          method: 'POST',
          headers: {{ authorization: {json.dumps(auth_header)} }},
        }};
        const res = {{
          code: null,
          body: null,
          status(code) {{
            this.code = code;
            return this;
          }},
          json(body) {{
            this.body = body;
            console.log(JSON.stringify({{ status: this.code, body, fetchCalls }}));
            return this;
          }},
        }};

        await handler(req, res);
        """
    )
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = "token_for_test"
    if cron_secret is None:
        env.pop("CRON_SECRET", None)
    else:
        env["CRON_SECRET"] = cron_secret
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


class CronWatchdogAuthTest(unittest.TestCase):
    def test_missing_cron_secret_fails_closed_before_fetch(self):
        out = run_cron_watchdog()

        self.assertEqual(out["status"], 401)
        self.assertEqual(out["body"], {"error": "unauthorized"})
        self.assertEqual(out["fetchCalls"], 0)

    def test_wrong_cron_secret_fails_before_fetch(self):
        out = run_cron_watchdog("Bearer wrong", cron_secret="right")

        self.assertEqual(out["status"], 401)
        self.assertEqual(out["body"], {"error": "unauthorized"})
        self.assertEqual(out["fetchCalls"], 0)


if __name__ == "__main__":
    unittest.main()
