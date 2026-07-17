import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_digest  # noqa: E402


class PublishDigestArchiveAssetsTest(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_root_assets_only(self):
        html = """<!doctype html>
<script src="js/site-config.js?v=1"></script>
<script src="https://cdn.example/chart.js"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
<link rel="preconnect" href="https://fonts.example">
<img src="images/logo.png">
"""

        out = publish_digest.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', out)
        self.assertIn('href="../css/digest.css?v=1"', out)
        self.assertIn('src="https://cdn.example/chart.js"', out)
        self.assertIn('href="https://fonts.example"', out)
        self.assertIn('src="images/logo.png"', out)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_dir = root / "docs" / "archive"
            archive_dir.mkdir(parents=True)
            manifest = archive_dir / "manifest.json"

            old_root = publish_digest.ROOT
            old_archive_dir = publish_digest.ARCHIVE_DIR
            old_manifest = publish_digest.MANIFEST
            publish_digest.ROOT = root
            publish_digest.ARCHIVE_DIR = archive_dir
            publish_digest.MANIFEST = manifest
            try:
                current_html = """<!doctype html>
<html><head>
<title>Market Digest</title>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head><body>
<main><header class="head"><h1>Thursday, July 16, 2026</h1>
<div class="meta">Test edition.</div></header></main>
</body></html>"""

                publish_digest.archive_previous_day(current_html, "2026-07-17")

                snapshot = (archive_dir / "2026-07-16.html").read_text()
                self.assertIn('src="../js/site-config.js?v=1"', snapshot)
                self.assertIn('href="../css/digest.css?v=1"', snapshot)
                self.assertIn("Archived", snapshot)

                entries = json.loads(manifest.read_text())
                self.assertEqual(entries[0]["date"], "2026-07-16")
            finally:
                publish_digest.ROOT = old_root
                publish_digest.ARCHIVE_DIR = old_archive_dir
                publish_digest.MANIFEST = old_manifest


if __name__ == "__main__":
    unittest.main()
