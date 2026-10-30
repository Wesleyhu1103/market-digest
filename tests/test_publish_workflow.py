import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def _step_block(name: str) -> str:
    text = WORKFLOW.read_text()
    match = re.search(
        rf"(?ms)^      - name: {re.escape(name)}\n(?P<body>.*?)(?=^      - name: |\Z)",
        text,
    )
    if not match:
        raise AssertionError(f"workflow step not found: {name}")
    return match.group(0)


class PublishWorkflowTests(unittest.TestCase):
    def test_static_only_deploy_does_not_apply_leftover_incoming_digest(self):
        step = _step_block("Apply incoming digest (archive + repair + splice)")

        self.assertIn("if: needs.plan.outputs.static != 'true'", step)
        self.assertIn("python3 scripts/publish_digest.py", step)


if __name__ == "__main__":
    unittest.main()
