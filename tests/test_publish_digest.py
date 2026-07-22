import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_digest  # noqa: E402


class PublishDigestArchiveTest(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_root_assets_only(self):
        html = (
            '<script src="js/app.js?v=1"></script>\n'
            '<link rel="stylesheet" href="css/digest.css?v=1">\n'
            '<script src="../js/already-safe.js?v=1"></script>\n'
            '<script src="https://cdn.example.com/js/app.js"></script>'
        )

        repaired = publish_digest.archive_safe_asset_paths(html)

        self.assertIn('src="../js/app.js?v=1"', repaired)
        self.assertIn('href="../css/digest.css?v=1"', repaired)
        self.assertIn('src="../js/already-safe.js?v=1"', repaired)
        self.assertIn('src="https://cdn.example.com/js/app.js"', repaired)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            old_archive_dir = publish_digest.ARCHIVE_DIR
            old_manifest = publish_digest.MANIFEST
            publish_digest.ARCHIVE_DIR = tmp_path / "archive"
            publish_digest.MANIFEST = publish_digest.ARCHIVE_DIR / "manifest.json"
            publish_digest.ARCHIVE_DIR.mkdir()
            try:
                current_html = """<!doctype html>
<html>
<head>
<script src="js/app.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head>
<body>
<main>
<h1>Tuesday, July 21, 2026</h1>
<div class="meta">Yesterday's digest</div>
</main>
</body>
</html>"""

                publish_digest.archive_previous_day(current_html, "2026-07-22")

                snapshot = (publish_digest.ARCHIVE_DIR / "2026-07-21.html").read_text()
                self.assertIn('src="../js/app.js?v=1"', snapshot)
                self.assertIn('href="../css/digest.css?v=1"', snapshot)
                manifest = json.loads(publish_digest.MANIFEST.read_text())
                self.assertEqual(manifest[0]["date"], "2026-07-21")
            finally:
                publish_digest.ARCHIVE_DIR = old_archive_dir
                publish_digest.MANIFEST = old_manifest


if __name__ == "__main__":
    unittest.main()
