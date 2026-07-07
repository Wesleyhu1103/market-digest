import subprocess
import textwrap
import unittest
from pathlib import Path


API = Path(__file__).resolve().parents[1] / "api" / "cron-watchdog.js"


class CronWatchdogTests(unittest.TestCase):
    def run_node(self, source: str):
        return subprocess.run(
            ["node", "--input-type=module"],
            input=source,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_cron_secret_is_required_before_any_network_calls(self):
        script = textwrap.dedent(
            f"""
            import handler from {API.as_uri()!r};

            delete process.env.CRON_SECRET;
            process.env.GITHUB_TOKEN = "dummy";

            let fetchCalled = false;
            globalThis.fetch = async () => {{
              fetchCalled = true;
              throw new Error("fetch should not run without CRON_SECRET");
            }};

            const res = {{
              code: undefined,
              body: undefined,
              status(code) {{
                this.code = code;
                return this;
              }},
              json(body) {{
                this.body = body;
                return this;
              }},
            }};

            await handler({{ method: "GET", headers: {{}} }}, res);

            if (res.code !== 401) {{
              throw new Error(`expected 401 without CRON_SECRET, got ${{res.code}} ${{JSON.stringify(res.body)}}`);
            }}
            if (fetchCalled) {{
              throw new Error("handler made network calls before authorization");
            }}
            """
        )

        result = self.run_node(script)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
