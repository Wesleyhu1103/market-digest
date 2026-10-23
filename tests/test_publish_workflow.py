from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def _workflow_step_block(step_name: str) -> str:
    text = WORKFLOW.read_text()
    marker = f"      - name: {step_name}"
    start = text.index(marker)
    next_step = text.find("\n      - name:", start + len(marker))
    if next_step == -1:
        next_step = len(text)
    return text[start:next_step]


class PublishWorkflowTests(unittest.TestCase):
    def test_static_only_deploy_does_not_apply_leftover_incoming_digest(self):
        block = _workflow_step_block("Apply incoming digest (archive + repair + splice)")

        self.assertIn("python3 scripts/publish_digest.py", block)
        self.assertIn("if: needs.plan.outputs.static != 'true'", block)


if __name__ == "__main__":
    unittest.main()
