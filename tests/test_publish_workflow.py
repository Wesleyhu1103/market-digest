import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


class PublishWorkflowTests(unittest.TestCase):
    def workflow_text(self):
        return WORKFLOW.read_text()

    def test_manual_dispatch_does_not_regenerate_current_digest(self):
        text = self.workflow_text()
        block = text[
            text.index('if [ "$EVENT" = "workflow_dispatch" ]; then'):
            text.index('if [ "$EVENT" = "schedule" ]; then')
        ]

        self.assertIn("Manual run found incoming/new-main.html", block)
        self.assertIn("Digest already current; skipping manual regeneration", block)
        self.assertRegex(
            block,
            re.compile(
                r"if python3 scripts/digest_stale\.py; then"
                r"[\s\S]*echo \"run=false\" >> \"\$GITHUB_OUTPUT\"",
            ),
        )

    def test_generation_never_removes_or_overwrites_incoming_digest(self):
        text = self.workflow_text()
        self.assertNotIn("rm incoming/new-main.html", text)

        block = text[
            text.index("- name: Generate digest with Claude"):
            text.index("- name: Apply incoming digest")
        ]
        self.assertRegex(
            block,
            re.compile(
                r"if \[ -f incoming/new-main\.html \]; then"
                r"[\s\S]*publishing it without generation"
                r"[\s\S]*elif \[ -z \"\$ANTHROPIC_API_KEY\" \]; then",
            ),
        )


if __name__ == "__main__":
    unittest.main()
