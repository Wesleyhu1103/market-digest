"""Tests for scripts/call_admin_api.py and digest_stale.py --remote.

Both scripts are the network legs of the rewired automation (feedback
clustering through the deployed API; watchdog re-verifying against live
main before alarming), so their retry/fallback behavior is pinned here
with a real local HTTP server — stdlib only, like the rest of tests/.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CALL = ROOT / "scripts" / "call_admin_api.py"
STALE = ROOT / "scripts" / "digest_stale.py"


class ScriptedHandler(BaseHTTPRequestHandler):
    """Serves a scripted list of (status, body) responses in order."""

    script = []  # class attr, set per server
    seen = None

    def _respond(self):
        idx = min(len(type(self).seen), len(type(self).script) - 1)
        status, body = type(self).script[idx]
        type(self).seen.append((self.command, self.path))
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = _respond
    do_POST = _respond

    def log_message(self, *args):
        pass


def serve(script):
    handler = type("H", (ScriptedHandler,), {"script": script, "seen": []})
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, handler


def run_call(origin, *extra, bearer="test-secret"):
    return subprocess.run(
        [sys.executable, str(CALL), "--origin", origin, "--backoff-base", "1", *extra],
        capture_output=True,
        text=True,
        env={"FEEDBACK_ADMIN_SECRET": bearer, "PATH": "/usr/bin:/bin"},
        cwd=str(ROOT),
    )


def test_retries_5xx_then_succeeds(tmp_path):
    srv, handler = serve([(500, "{}"), (502, "{}"), (200, '{"ok":true,"created":2}')])
    out = tmp_path / "res.json"
    try:
        proc = run_call(
            f"http://127.0.0.1:{srv.server_port}",
            "--path", "/api/admin-proposals",
            "--body", '{"action":"process"}',
            "--out", str(out),
        )
    finally:
        srv.shutdown()
    assert proc.returncode == 0, proc.stderr
    assert len(handler.seen) == 3
    assert all(m == "POST" for m, _ in handler.seen)
    assert json.loads(out.read_text()) == {"ok": True, "created": 2}
    assert "retrying" in proc.stderr


def test_auth_error_fails_fast_no_retry(tmp_path):
    srv, handler = serve([(401, '{"error":"unauthorized"}')])
    try:
        proc = run_call(
            f"http://127.0.0.1:{srv.server_port}",
            "--path", "/api/admin-proposals?status=pending",
        )
    finally:
        srv.shutdown()
    assert proc.returncode == 1
    assert len(handler.seen) == 1  # 4xx must not retry
    assert "FEEDBACK_ADMIN_SECRET" in proc.stderr  # actionable hint


def test_missing_bearer_env_is_a_distinct_error():
    proc = run_call("http://127.0.0.1:9", "--path", "/x", bearer="")
    assert proc.returncode == 2
    assert "not set" in proc.stderr


def test_connection_refused_exhausts_retries():
    srv, _ = serve([(200, "{}")])
    port = srv.server_port
    srv.shutdown()
    srv.server_close()  # port now refuses connections
    proc = run_call(f"http://127.0.0.1:{port}", "--path", "/x", "--retries", "2")
    assert proc.returncode == 1
    assert "failed after 2 attempt(s)" in proc.stderr


def _html_for(date_iso):
    return f"<html><body><h1>{datetime.strptime(date_iso, '%Y-%m-%d').strftime('%A, %B %d, %Y')}</h1></body></html>"


def _today_et():
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def run_stale(*args):
    return subprocess.run(
        [sys.executable, str(STALE), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT / "scripts"),
    )


def test_remote_stale_detected():
    srv, _ = serve([(200, _html_for("2020-01-02"))])
    try:
        proc = run_stale("--remote", f"http://127.0.0.1:{srv.server_port}/index.html")
    finally:
        srv.shutdown()
    assert proc.returncode == 1
    assert "digest_date=2020-01-02" in proc.stdout


def test_remote_current_detected():
    srv, _ = serve([(200, _html_for(_today_et()))])
    try:
        proc = run_stale("--remote", f"http://127.0.0.1:{srv.server_port}/index.html")
    finally:
        srv.shutdown()
    assert proc.returncode == 0
    assert "stale=false" in proc.stdout


def test_remote_fetch_failure_falls_back_to_local():
    # Closed port: remote unreachable -> falls back to the checkout's
    # docs/index.html rather than crashing or silently reporting current.
    srv, _ = serve([(200, "{}")])
    port = srv.server_port
    srv.shutdown()
    srv.server_close()
    proc = run_stale("--remote", f"http://127.0.0.1:{port}/index.html")
    assert proc.returncode in (0, 1)  # verdict comes from the local file
    assert "remote fetch failed" in proc.stdout
    assert "digest_date=" in proc.stdout
