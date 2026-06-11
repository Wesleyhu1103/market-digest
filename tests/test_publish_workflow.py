import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


class PublishWorkflowTests(unittest.TestCase):
    def test_current_scheduled_run_is_fred_only(self):
        workflow = WORKFLOW.read_text()

        remove_incoming = (
            'if [ "$EVENT_NAME" = "schedule" ] && [ -f incoming/new-main.html ]; then\n'
            '            echo "Removing stale incoming/new-main.html before scheduled run"\n'
            "            rm incoming/new-main.html\n"
            "          fi"
        )
        skip_generation = (
            'if [ "$EVENT_NAME" = "schedule" ] && [ "$STALE" != "true" ]; then\n'
            '            echo "Digest is current; running scheduled FRED refresh only"\n'
            "            exit 0\n"
            "          fi"
        )
        require_key = 'if [ -z "$ANTHROPIC_API_KEY" ]; then'

        self.assertIn(remove_incoming, workflow)
        self.assertIn(skip_generation, workflow)
        self.assertLess(workflow.index(remove_incoming), workflow.index(skip_generation))
        self.assertLess(workflow.index(skip_generation), workflow.index(require_key))


if __name__ == "__main__":
    unittest.main()
