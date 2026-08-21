import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish-digest.yml"


def workflow_text():
    return WORKFLOW.read_text()


def step_block(text, name):
    match = re.search(
        rf"(?ms)^      - name: {re.escape(name)}\n(?P<body>.*?)(?=^      - name: |\Z)",
        text,
    )
    if not match:
        raise AssertionError(f"Step not found: {name}")
    return match.group("body")


class PublishWorkflowTests(unittest.TestCase):
    def test_manual_dispatch_does_not_republish_current_digest_without_incoming(self):
        text = workflow_text()
        dispatch_block = re.search(
            r'(?ms)if \[ "\$EVENT" = "workflow_dispatch" \]; then(?P<body>.*?)exit 0',
            text,
        )
        self.assertIsNotNone(dispatch_block)
        body = dispatch_block.group("body")
        self.assertIn("incoming/new-main.html present; publishing prepared digest", body)
        self.assertIn("Digest already current; skipping manual publish without incoming digest", body)
        self.assertIn('echo "run=false" >> "$GITHUB_OUTPUT"', body)

    def test_generation_is_gated_by_build_time_freshness_recheck(self):
        text = workflow_text()
        freshness = step_block(text, "Re-check digest freshness")
        generate = step_block(text, "Generate digest with Claude")

        self.assertIn("python3 scripts/digest_stale.py", freshness)
        self.assertIn('echo "stale=false" >> "$GITHUB_OUTPUT"', freshness)
        self.assertIn('echo "stale=true" >> "$GITHUB_OUTPUT"', freshness)
        self.assertIn(
            "if: needs.plan.outputs.static != 'true' && steps.freshness.outputs.stale == 'true'",
            generate,
        )
        self.assertNotIn("github.event_name != 'push'", generate)

    def test_generation_preserves_prepared_incoming_digest(self):
        generate = step_block(workflow_text(), "Generate digest with Claude")

        self.assertIn("incoming/new-main.html already present; skipping generation", generate)
        self.assertNotIn("rm incoming/new-main.html", generate)

    def test_static_deploys_do_not_run_publish_digest(self):
        apply = step_block(workflow_text(), "Apply incoming digest (archive + repair + splice)")

        self.assertIn("if: needs.plan.outputs.static != 'true'", apply)
        self.assertIn("python3 scripts/publish_digest.py", apply)


if __name__ == "__main__":
    unittest.main()
