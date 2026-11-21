import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_step(name: str) -> str:
    text = WORKFLOW.read_text()
    marker = f"      - name: {name}\n"
    start = text.index(marker)
    next_step = re.search(r"\n      - name: ", text[start + len(marker):])
    end = start + len(marker) + next_step.start() if next_step else len(text)
    return text[start:end]


class PublishWorkflowTests(unittest.TestCase):
    def test_static_deploys_do_not_apply_incoming_digest(self):
        step = workflow_step("Apply incoming digest (archive + repair + splice)")

        self.assertIn("if: needs.plan.outputs.static != 'true'", step)
        self.assertIn("python3 scripts/publish_digest.py", step)


if __name__ == "__main__":
    unittest.main()
