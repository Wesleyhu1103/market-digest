import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


class PublishWorkflowTests(unittest.TestCase):
    def test_static_redeploy_does_not_apply_incoming_digest(self):
        text = WORKFLOW.read_text()
        block = re.search(
            r"- name: Apply incoming digest \(archive \+ repair \+ splice\)\n(?P<body>(?:        .+\n)+)",
            text,
        )
        self.assertIsNotNone(block)
        self.assertIn("if: needs.plan.outputs.static != 'true'", block.group("body"))


if __name__ == "__main__":
    unittest.main()
