import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_step(name: str) -> str:
    text = WORKFLOW.read_text()
    match = re.search(
        rf"^      - name: {re.escape(name)}\n(?P<body>(?:        .+\n)+)",
        text,
        flags=re.MULTILINE,
    )
    if not match:
        raise AssertionError(f"workflow step not found: {name}")
    return match.group(0)


class PublishWorkflowTests(unittest.TestCase):
    def test_static_only_deploys_do_not_apply_leftover_incoming_digest(self):
        step = workflow_step("Apply incoming digest (archive + repair + splice)")

        self.assertIn("if: needs.plan.outputs.static != 'true'", step)
        self.assertIn("run: python3 scripts/publish_digest.py", step)


if __name__ == "__main__":
    unittest.main()
