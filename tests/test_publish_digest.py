import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_digest  # noqa: E402


class PublishDigestArchiveTests(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        html = """<!doctype html>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
<script src="../js/already-archive-safe.js?v=1"></script>
<script src="https://cdn.example.com/js/lib.js"></script>
<a href="css/not-a-link-asset.css">download</a>
"""

        rewritten = publish_digest.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('src="../js/already-archive-safe.js?v=1"', rewritten)
        self.assertIn('src="https://cdn.example.com/js/lib.js"', rewritten)
        self.assertIn('href="css/not-a-link-asset.css"', rewritten)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        current_html = """<!doctype html>
<html><head>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head><body>
<main><header class="head"><h1>Monday, July 13, 2026</h1><div class="meta">Yesterday's digest.</div></header></main>
</body></html>"""

        old_archive_dir = publish_digest.ARCHIVE_DIR
        old_manifest = publish_digest.MANIFEST
        old_root = publish_digest.ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                publish_digest.ROOT = tmp_path
                publish_digest.ARCHIVE_DIR = tmp_path / "archive"
                publish_digest.MANIFEST = publish_digest.ARCHIVE_DIR / "manifest.json"
                publish_digest.ARCHIVE_DIR.mkdir()

                publish_digest.archive_previous_day(current_html, "2026-07-14")
                snapshot = (publish_digest.ARCHIVE_DIR / "2026-07-13.html").read_text()

                self.assertIn('src="../js/site-config.js?v=1"', snapshot)
                self.assertIn('href="../css/digest.css?v=1"', snapshot)
                self.assertIn("Archived -- 2026-07-13", snapshot.replace("—", "--"))
        finally:
            publish_digest.ROOT = old_root
            publish_digest.ARCHIVE_DIR = old_archive_dir
            publish_digest.MANIFEST = old_manifest


if __name__ == "__main__":
    unittest.main()
