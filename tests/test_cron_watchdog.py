import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CRON_WATCHDOG = ROOT / "api" / "cron-watchdog.js"


class CronWatchdogAuthTest(unittest.TestCase):
    def test_missing_cron_secret_fails_closed_before_fetch(self):
        src = CRON_WATCHDOG.read_text()
        auth_fn = re.search(r"function authorizeCron\(req\) \{(?P<body>.*?)\n\}", src, re.S)
        self.assertIsNotNone(auth_fn, "authorizeCron function not found")
        body = auth_fn.group("body")
        self.assertRegex(body, r"if \(!secret\)\s+return false;")
        self.assertNotRegex(body, r"if \(!secret\)\s+return true;")

        handler_body = re.search(
            r"export default async function handler\(req, res\) \{(?P<body>.*)\n\}",
            src,
            re.S,
        ).group("body")
        auth_pos = handler_body.find("authorizeCron(req)")
        fetch_pos = handler_body.find("fetch(INDEX_URL")
        self.assertGreaterEqual(auth_pos, 0, "handler does not call authorizeCron")
        self.assertGreaterEqual(fetch_pos, 0, "handler does not fetch the index")
        self.assertLess(auth_pos, fetch_pos, "cron auth must run before any network fetch")


if __name__ == "__main__":
    unittest.main()
