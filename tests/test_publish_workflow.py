import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


class PublishWorkflowTests(unittest.TestCase):
    def _step_block(self, step_name: str) -> str:
        text = WORKFLOW.read_text()
        match = re.search(
            rf"(?ms)^      - name: {re.escape(step_name)}\n"
            r"(?P<body>.*?)(?=^      - name: |\Z)",
            text,
        )
        self.assertIsNotNone(match, f"missing workflow step: {step_name}")
        return match.group(0)

    def test_static_deploys_do_not_apply_committed_incoming_digest(self):
        step = self._step_block("Apply incoming digest (archive + repair + splice)")

        self.assertIn("if: needs.plan.outputs.static != 'true'", step)
        self.assertIn("run: python3 scripts/publish_digest.py", step)


if __name__ == "__main__":
    unittest.main()
