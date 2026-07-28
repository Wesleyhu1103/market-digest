"""Security regression tests for the Vercel cron watchdog auth gate."""
from __future__ import annotations

import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CronWatchdogAuthTest(unittest.TestCase):
    def test_cron_secret_is_required_and_must_match_bearer(self):
        script = textwrap.dedent(
            """
            import { authorizeCron } from './api/_cron_auth.js';

            function req(auth) {
              return { headers: auth ? { authorization: auth } : {} };
            }

            const cases = [
              ['unset secret rejects missing auth', undefined, undefined, false],
              ['unset secret rejects arbitrary auth', undefined, 'Bearer anything', false],
              ['set secret accepts exact bearer', 's3cr3t', 'Bearer s3cr3t', true],
              ['set secret rejects missing auth', 's3cr3t', undefined, false],
              ['set secret rejects wrong bearer', 's3cr3t', 'Bearer wrong', false],
            ];

            for (const [name, secret, auth, expected] of cases) {
              if (secret === undefined) delete process.env.CRON_SECRET;
              else process.env.CRON_SECRET = secret;
              const actual = authorizeCron(req(auth));
              if (actual !== expected) {
                throw new Error(`${name}: expected ${expected}, got ${actual}`);
              }
            }
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
