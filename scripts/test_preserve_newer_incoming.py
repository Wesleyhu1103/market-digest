#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("preserve_newer_incoming.py")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)


class PreserveNewerIncomingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "workflow"
        self.other = self.root / "other"

        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)
        git(self.repo, "config", "user.name", "Test User")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "remote", "add", "origin", str(self.remote))

        incoming = self.repo / "incoming" / "new-main.html"
        incoming.parent.mkdir()
        incoming.write_text("<main>old digest</main>\n")
        commit_all(self.repo, "Initial incoming digest")
        git(self.repo, "push", "-u", "origin", "main")
        self.processed_sha = git(self.repo, "hash-object", "incoming/new-main.html")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_helper(self, processed_sha: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PRESERVE_INCOMING_ROOT"] = str(self.repo)
        return subprocess.run(
            [sys.executable, str(SCRIPT), processed_sha],
            cwd=self.repo,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

    def push_newer_incoming_from_other_clone(self) -> None:
        subprocess.run(["git", "clone", str(self.remote), str(self.other)], check=True, capture_output=True)
        git(self.other, "config", "user.name", "Other User")
        git(self.other, "config", "user.email", "other@example.com")
        (self.other / "incoming" / "new-main.html").write_text("<main>new digest</main>\n")
        commit_all(self.other, "Queue newer incoming digest")
        git(self.other, "push", "origin", "main")

    def test_restores_newer_remote_incoming_after_local_cleanup(self) -> None:
        (self.repo / "incoming" / "new-main.html").unlink()
        self.push_newer_incoming_from_other_clone()

        result = self.run_helper(self.processed_sha)

        self.assertIn("Restored newer incoming/new-main.html", result.stdout)
        self.assertEqual(
            "<main>new digest</main>\n",
            (self.repo / "incoming" / "new-main.html").read_text(),
        )

    def test_allows_cleanup_when_remote_matches_processed_digest(self) -> None:
        (self.repo / "incoming" / "new-main.html").unlink()

        result = self.run_helper(self.processed_sha)

        self.assertIn("matches processed digest", result.stdout)
        self.assertFalse((self.repo / "incoming" / "new-main.html").exists())


if __name__ == "__main__":
    unittest.main()
