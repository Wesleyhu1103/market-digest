from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-digest.yml"


def test_static_deploy_does_not_apply_leftover_incoming_digest():
    """Static docs/API deploys must not splice any tracked incoming digest."""
    lines = WORKFLOW.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "- name: Apply incoming digest (archive + repair + splice)":
            block = lines[i : i + 3]
            break
    else:
        raise AssertionError("Apply incoming digest step not found")

    assert "if: needs.plan.outputs.static != 'true'" in [part.strip() for part in block]
