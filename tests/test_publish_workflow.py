import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_step(name: str) -> str:
    text = WORKFLOW.read_text()
    match = re.search(
        rf"(?ms)^      - name: {re.escape(name)}\n(?P<body>.*?)(?=^      - name: |\Z)",
        text,
    )
    if not match:
        raise AssertionError(f"workflow step not found: {name}")
    return match.group("body")


class PublishWorkflowTests(unittest.TestCase):
    def test_static_deploys_do_not_apply_committed_incoming_digest(self):
        step = workflow_step("Apply incoming digest (archive + repair + splice)")

        self.assertIn("if: needs.plan.outputs.static != 'true'", step)
        self.assertIn("run: python3 scripts/publish_digest.py", step)


if __name__ == "__main__":
    unittest.main()
