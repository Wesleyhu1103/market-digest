import subprocess
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "api" / "cron-watchdog.js"


class CronWatchdogTests(unittest.TestCase):
    def test_missing_cron_secret_fails_closed_before_network(self):
        node = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            let source = fs.readFileSync({str(SCRIPT)!r}, 'utf8');
            source = source.replace(
              'export default async function handler(req, res)',
              'async function handler(req, res)'
            );
            source += '\\nmodule.exports = {{ handler, authorizeCron }};';

            let fetched = false;
            const context = {{
              module: {{ exports: {{}} }},
              console,
              process: {{ env: {{ GITHUB_TOKEN: 'dummy' }} }},
              fetch: async function() {{ fetched = true; throw new Error('fetch should not run'); }},
              Intl,
              Date,
              JSON,
              Error,
            }};
            vm.runInNewContext(source, context);

            let statusCode = null;
            let body = null;
            const res = {{
              status(code) {{
                statusCode = code;
                return {{ json(payload) {{ body = payload; }} }};
              }}
            }};

            (async () => {{
              await context.module.exports.handler({{ method: 'GET', headers: {{}} }}, res);
              if (statusCode !== 401) throw new Error('expected 401, got ' + statusCode);
              if (!body || body.error !== 'unauthorized') throw new Error('expected unauthorized body');
              if (fetched) throw new Error('fetch ran before auth failed');
            }})().catch((err) => {{
              console.error(err.message);
              process.exit(1);
            }});
            """
        )

        result = subprocess.run(["node", "-e", node], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
