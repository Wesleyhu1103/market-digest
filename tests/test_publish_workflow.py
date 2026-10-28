import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_step(name: str) -> str:
    lines = WORKFLOW.read_text().splitlines()
    marker = f"      - name: {name}"
    for idx, line in enumerate(lines):
        if line == marker:
            block = [line]
            for next_line in lines[idx + 1 :]:
                if next_line.startswith("      - name: ") or next_line.startswith("  deploy:"):
                    break
                block.append(next_line)
            return "\n".join(block)
    raise AssertionError(f"missing workflow step: {name}")


class PublishWorkflowTests(unittest.TestCase):
    def test_static_deploy_does_not_apply_leftover_incoming_digest(self):
        step = workflow_step("Apply incoming digest (archive + repair + splice)")
        self.assertIn("if: needs.plan.outputs.static != 'true'", step)
        self.assertIn("python3 scripts/publish_digest.py", step)


if __name__ == "__main__":
    unittest.main()
