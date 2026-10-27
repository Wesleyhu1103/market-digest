import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_step(name):
    text = WORKFLOW.read_text()
    match = re.search(
        rf"(?ms)^      - name: {re.escape(name)}\n(?P<body>.*?)(?=^      - name:|^  [a-zA-Z0-9_-]+:|\Z)",
        text,
    )
    assert match, f"workflow step not found: {name}"
    return match.group("body")


class PublishWorkflowTests(unittest.TestCase):
    def test_static_deploy_does_not_apply_committed_incoming_digest(self):
        apply_step = workflow_step("Apply incoming digest (archive + repair + splice)")

        self.assertIn("run: python3 scripts/publish_digest.py", apply_step)
        self.assertIn("if: needs.plan.outputs.static != 'true'", apply_step)


if __name__ == "__main__":
    unittest.main()
