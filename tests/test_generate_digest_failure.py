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

    class APIConnectionError(Exception):
        pass

    stub.APIStatusError = APIStatusError
    stub.APIConnectionError = APIConnectionError
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


# Mimics the SDK's vendored transport errors (seen in prod as module
# "httpx2"), which must be matched by module name, not by import identity.
def _vendored_httpx_error():
    err_cls = type("RemoteProtocolError", (Exception,), {"__module__": "httpx2"})
    return err_cls("peer closed connection without sending complete message body")


def test_transient_classifier(monkeypatch, tmp_path):
    mod, _ = _load_generate_digest(monkeypatch, tmp_path)
    anthropic_stub = sys.modules["anthropic"]
    assert mod.is_transient_generation_error(_vendored_httpx_error())
    assert mod.is_transient_generation_error(anthropic_stub.APIConnectionError("down"))
    assert mod.is_transient_generation_error(anthropic_stub.APIStatusError("overloaded", 529))
    assert mod.is_transient_generation_error(anthropic_stub.APIStatusError("rate", 429))
    assert not mod.is_transient_generation_error(anthropic_stub.APIStatusError("credits", 400))
    assert not mod.is_transient_generation_error(ValueError("bad output"))


class _FakeStreamCtx:
    def __init__(self, fail_times, final):
        self.fail_times = fail_times
        self.final = final

    def __enter__(self):
        if self.fail_times[0] > 0:
            self.fail_times[0] -= 1
            raise _vendored_httpx_error()
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.final


class _FakeClient:
    def __init__(self, fail_times, final="FINAL"):
        self.calls = 0
        self._fail = [fail_times]
        self._final = final
        outer = self

        class _Messages:
            def stream(self, **kwargs):
                outer.calls += 1
                return _FakeStreamCtx(outer._fail, outer._final)

        self.messages = _Messages()


def test_generate_message_retries_transient_then_succeeds(monkeypatch, tmp_path):
    mod, _ = _load_generate_digest(monkeypatch, tmp_path)
    client = _FakeClient(fail_times=2)
    assert mod.generate_message(client, "content", attempts=3, backoff=0) == "FINAL"
    assert client.calls == 3


def test_generate_message_gives_up_after_attempts(monkeypatch, tmp_path):
    mod, _ = _load_generate_digest(monkeypatch, tmp_path)
    client = _FakeClient(fail_times=99)
    try:
        mod.generate_message(client, "content", attempts=3, backoff=0)
        raise AssertionError("expected the transport error to re-raise")
    except Exception as e:
        assert type(e).__module__ == "httpx2"
    assert client.calls == 3


def test_generate_message_fatal_error_not_retried(monkeypatch, tmp_path):
    mod, _ = _load_generate_digest(monkeypatch, tmp_path)
    anthropic_stub = sys.modules["anthropic"]
    client = _FakeClient(fail_times=0)

    def _raise_billing(**kwargs):
        client.calls += 1
        raise anthropic_stub.APIStatusError("credit balance is too low", 400)

    client.messages.stream = _raise_billing
    try:
        mod.generate_message(client, "content", attempts=3, backoff=0)
        raise AssertionError("expected the billing error to re-raise")
    except anthropic_stub.APIStatusError:
        pass
    assert client.calls == 1
