import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


class PublishWorkflowTests(unittest.TestCase):
    def test_static_deploys_do_not_apply_leftover_incoming_digest(self):
        text = WORKFLOW.read_text()
        match = re.search(
            r"\n      - name: Apply incoming digest \(archive \+ repair \+ splice\)"
            r"(?P<step>[\s\S]*?)(?=\n      - name:|\n  [a-zA-Z_])",
            text,
        )
        self.assertIsNotNone(match, "publish workflow must keep an explicit apply step")
        step = match.group("step")

        self.assertIn("run: python3 scripts/publish_digest.py", step)
        self.assertIn("if: needs.plan.outputs.static != 'true'", step)


if __name__ == "__main__":
    unittest.main()
