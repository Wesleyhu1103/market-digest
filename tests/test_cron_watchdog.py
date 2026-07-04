import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_node(script):
    return subprocess.run(
        ["node", "--input-type=module"],
        cwd=ROOT,
        input=textwrap.dedent(script),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


class CronWatchdogAuthTests(unittest.TestCase):
    def test_missing_cron_secret_fails_closed_before_network(self):
        run_node(
            """
            const { default: handler } = await import("./api/cron-watchdog.js");
            delete process.env.CRON_SECRET;
            process.env.GITHUB_TOKEN = "dummy";
            globalThis.fetch = async () => {
              throw new Error("fetch should not run before auth succeeds");
            };

            let statusCode = null;
            let payload = null;
            const res = {
              status(code) { statusCode = code; return this; },
              json(body) { payload = body; },
            };

            await handler({ method: "GET", headers: {}, socket: {} }, res);
            if (statusCode !== 401) {
              throw new Error(`expected 401, got ${statusCode}`);
            }
            if (!payload || payload.error !== "unauthorized") {
              throw new Error(`unexpected payload ${JSON.stringify(payload)}`);
            }
            """
        )

    def test_wrong_cron_secret_fails_before_network(self):
        run_node(
            """
            const { default: handler } = await import("./api/cron-watchdog.js");
            process.env.CRON_SECRET = "expected";
            process.env.GITHUB_TOKEN = "dummy";
            globalThis.fetch = async () => {
              throw new Error("fetch should not run before auth succeeds");
            };

            let statusCode = null;
            const res = {
              status(code) { statusCode = code; return this; },
              json(_) {},
            };

            await handler(
              { method: "GET", headers: { authorization: "Bearer wrong" }, socket: {} },
              res,
            );
            if (statusCode !== 401) {
              throw new Error(`expected 401, got ${statusCode}`);
            }
            """
        )


if __name__ == "__main__":
    unittest.main()
