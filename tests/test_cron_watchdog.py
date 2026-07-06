import json
import os
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_handler(env, headers=None, html=None):
    headers = headers or {}
    fetch_impl = (
        "async () => { throw new Error('fetch should not be called'); }"
        if html is None
        else textwrap.dedent(
            f"""
            async () => ({{
              ok: true,
              async text() {{ return {json.dumps(html)}; }}
            }})
            """
        )
    )
    script = textwrap.dedent(
        f"""
        import handler from './api/cron-watchdog.js';

        global.fetch = {fetch_impl};

        const req = {{
          method: 'GET',
          headers: {json.dumps(headers)}
        }};
        const res = {{
          statusCode: 200,
          payload: null,
          status(code) {{
            this.statusCode = code;
            return this;
          }},
          json(payload) {{
            this.payload = payload;
            console.log(JSON.stringify({{ statusCode: this.statusCode, payload }}));
            return this;
          }}
        }};

        await handler(req, res);
        """
    )
    node_env = os.environ.copy()
    node_env.update(env)
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        env=node_env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


class CronWatchdogTests(unittest.TestCase):
    def test_missing_cron_secret_fails_closed_before_network(self):
        response = run_handler({"CRON_SECRET": "", "GITHUB_TOKEN": "dummy"})

        self.assertEqual(response["statusCode"], 401)
        self.assertEqual(response["payload"]["error"], "unauthorized")

    def test_wrong_cron_secret_fails_closed_before_network(self):
        response = run_handler(
            {"CRON_SECRET": "secret", "GITHUB_TOKEN": "dummy"},
            headers={"authorization": "Bearer wrong"},
        )

        self.assertEqual(response["statusCode"], 401)
        self.assertEqual(response["payload"]["error"], "unauthorized")

    def test_valid_cron_secret_allows_stale_check(self):
        response = run_handler(
            {"CRON_SECRET": "secret"},
            headers={"authorization": "Bearer secret"},
            html="<script>date: '2999-01-01'</script>",
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["payload"]["action"], "skip")
        self.assertFalse(response["payload"]["stale"])


if __name__ == "__main__":
    unittest.main()
