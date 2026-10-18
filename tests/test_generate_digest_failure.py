# Pin generate_digest.py's failure-reason recording: on any failure the
# script must leave a one-line cause at DIGEST_FAILURE_REASON_FILE (read by
# publish-digest.yml's maintenance-flag step) and emit a ::error annotation.
# anthropic is stubbed so the test runs without the package installed.
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_generate_digest(monkeypatch, tmp_path):
    stub = types.ModuleType("anthropic")

    class APIStatusError(Exception):
        def __init__(self, message="boom", status_code=400):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    stub.APIStatusError = APIStatusError
    stub.Anthropic = object
    monkeypatch.setitem(sys.modules, "anthropic", stub)
    monkeypatch.setenv("DIGEST_FAILURE_REASON_FILE", str(tmp_path / "reason.txt"))
    spec = importlib.util.spec_from_file_location(
        "generate_digest_under_test", ROOT / "scripts" / "generate_digest.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, tmp_path / "reason.txt"


def test_record_failure_writes_reason_file_and_error_annotation(monkeypatch, tmp_path, capsys):
    mod, reason_file = _load_generate_digest(monkeypatch, tmp_path)
    mod._record_failure("ABORT: only 3 fresh feed items\nin last 36h")
    assert reason_file.read_text() == "ABORT: only 3 fresh feed items in last 36h"
    assert "::error::Digest generation failed: ABORT" in capsys.readouterr().err


def test_record_failure_truncates_and_never_raises(monkeypatch, tmp_path):
    mod, reason_file = _load_generate_digest(monkeypatch, tmp_path)
    mod._record_failure("x" * 5000)
    assert len(reason_file.read_text()) == 1000
    # Unwritable path must not mask the original failure.
    monkeypatch.setenv("DIGEST_FAILURE_REASON_FILE", "/nonexistent-dir/reason.txt")
    mod._record_failure("still fine")
