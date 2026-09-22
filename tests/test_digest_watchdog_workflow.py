import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "digest-watchdog.yml"


class DigestWatchdogWorkflowTests(unittest.TestCase):
    def test_in_progress_publish_runs_late_stale_alarm_before_green_exit(self):
        text = WORKFLOW.read_text()
        in_progress = 'if [ "$RUNNING" != "0" ]; then'
        block_start = text.index(in_progress)
        block_end = text.index("echo \"Digest is stale; dispatching", block_start)
        block = text[block_start:block_end]

        self.assertIn("late_stale_alarm", block)
        self.assertLess(block.index("late_stale_alarm"), block.index("exit 0"))

    def test_late_alarm_rechecks_remote_main_and_posts_critical_flag(self):
        text = WORKFLOW.read_text()

        self.assertIn("late_stale_alarm()", text)
        self.assertIn("scripts/digest_stale.py --remote", text)
        self.assertIn("--source digest-watchdog --severity critical", text)


if __name__ == "__main__":
    unittest.main()
