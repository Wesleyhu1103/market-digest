import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_step(name: str) -> str:
    text = WORKFLOW.read_text()
    marker = f"      - name: {name}\n"
    start = text.index(marker)
    next_step = text.find("\n      - name:", start + len(marker))
    return text[start:] if next_step == -1 else text[start:next_step]


class PublishWorkflowTests(unittest.TestCase):
    def test_static_deploys_do_not_apply_committed_incoming_digest(self):
        step = workflow_step("Apply incoming digest (archive + repair + splice)")

        self.assertIn("run: python3 scripts/publish_digest.py", step)
        self.assertIn("if: needs.plan.outputs.static != 'true'", step)


if __name__ == "__main__":
    unittest.main()
