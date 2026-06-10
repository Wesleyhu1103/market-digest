#!/usr/bin/env python3
"""Keep a newer queued incoming digest from being deleted by a publish run.

The publish workflow removes incoming/new-main.html after processing it. If
another digest is pushed while the workflow is running, origin/main can already
contain a different incoming/new-main.html by the time the workflow commits.
Restore that newer remote blob before staging so the queued workflow run can
publish it next.
"""
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(
    os.environ.get("PRESERVE_INCOMING_ROOT", Path(__file__).resolve().parents[1])
).resolve()
INCOMING = ROOT / "incoming" / "new-main.html"
REMOTE_REF = "origin/main"
REMOTE_PATH = f"{REMOTE_REF}:incoming/new-main.html"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def git_bytes(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def remote_incoming_sha() -> str | None:
    result = git("rev-parse", "--verify", REMOTE_PATH, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def restore_remote_incoming() -> None:
    INCOMING.parent.mkdir(parents=True, exist_ok=True)
    INCOMING.write_bytes(git_bytes("show", REMOTE_PATH))


def main() -> int:
    processed_sha = sys.argv[1].strip() if len(sys.argv) > 1 else ""

    git("fetch", "origin", "main")
    remote_sha = remote_incoming_sha()
    if remote_sha is None:
        print("No incoming/new-main.html on origin/main to preserve.")
        return 0

    if remote_sha == processed_sha:
        print("Remote incoming digest matches processed digest; allowing cleanup.")
        return 0

    restore_remote_incoming()
    print("Restored newer incoming/new-main.html from origin/main for queued publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
