import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_step_block(step_name: str) -> str:
    lines = WORKFLOW.read_text().splitlines()
    marker = f"      - name: {step_name}"
    start = lines.index(marker)
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("      - name: "):
            end = idx
            break
    return "\n".join(lines[start:end])


class PublishWorkflowTests(unittest.TestCase):
    def test_static_only_build_does_not_splice_leftover_incoming_digest(self):
        block = workflow_step_block("Apply incoming digest (archive + repair + splice)")

        self.assertIn("if: needs.plan.outputs.static != 'true'", block)
        self.assertIn("run: python3 scripts/publish_digest.py", block)


if __name__ == "__main__":
    unittest.main()
