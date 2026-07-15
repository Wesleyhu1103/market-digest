import subprocess
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "api" / "cron-watchdog.js"


class CronWatchdogTests(unittest.TestCase):
    def test_authorize_cron_fails_closed_without_secret(self):
        js = textwrap.dedent(
            f"""
            import {{ authorizeCron }} from {SCRIPT.as_uri()!r};

            delete process.env.CRON_SECRET;
            if (authorizeCron({{ headers: {{}} }}) !== false) {{
              throw new Error('missing CRON_SECRET must reject');
            }}

            process.env.CRON_SECRET = 'sekret';
            if (authorizeCron({{ headers: {{ authorization: 'Bearer wrong' }} }}) !== false) {{
              throw new Error('wrong bearer token must reject');
            }}
            if (authorizeCron({{ headers: {{ authorization: 'Bearer sekret' }} }}) !== true) {{
              throw new Error('matching bearer token must pass');
            }}
            """
        )

        result = subprocess.run(
            ["node", "--input-type=module", "-e", js],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
