import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-digest.yml"


def _workflow_step(name: str) -> str:
    lines = WORKFLOW.read_text().splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.strip() == f"- name: {name}"
    )
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("      - name: "):
            end = i
            break
    return "\n".join(lines[start:end])


class PublishWorkflowTests(unittest.TestCase):
    def test_static_deploys_do_not_apply_incoming_digest(self):
        step = _workflow_step("Apply incoming digest (archive + repair + splice)")

        self.assertIn("run: python3 scripts/publish_digest.py", step)
        self.assertIn("if: needs.plan.outputs.static != 'true'", step)


if __name__ == "__main__":
    unittest.main()
