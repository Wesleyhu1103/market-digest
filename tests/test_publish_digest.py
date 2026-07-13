import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_digest  # noqa: E402


class PublishDigestArchiveTest(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        html = """
        <script src="js/site-config.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        <script src="../js/already-archive-safe.js"></script>
        <script src="https://example.test/js/remote.js"></script>
        <a href="archive/2026-07-10.html">Archive</a>
        """

        rewritten = publish_digest.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('src="../js/already-archive-safe.js"', rewritten)
        self.assertIn('src="https://example.test/js/remote.js"', rewritten)
        self.assertIn('href="archive/2026-07-10.html"', rewritten)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        html = """
        <!doctype html>
        <html>
        <head>
        <title>Market Digest - Fri Jul 10, 2026</title>
        <script src="js/site-config.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        </head>
        <body>
        <h1>Friday, July 10, 2026</h1>
        <div class="meta">Test digest summary.</div>
        <main><section>Old digest</section></main>
        </body>
        </html>
        """

        with tempfile.TemporaryDirectory() as td:
            archive_dir = Path(td) / "archive"
            archive_dir.mkdir()
            old_root = publish_digest.ROOT
            old_archive_dir = publish_digest.ARCHIVE_DIR
            old_manifest = publish_digest.MANIFEST
            publish_digest.ROOT = Path(td)
            publish_digest.ARCHIVE_DIR = archive_dir
            publish_digest.MANIFEST = archive_dir / "manifest.json"
            try:
                publish_digest.archive_previous_day(html, "2026-07-13")
            finally:
                publish_digest.ROOT = old_root
                publish_digest.ARCHIVE_DIR = old_archive_dir
                publish_digest.MANIFEST = old_manifest

            snapshot = (archive_dir / "2026-07-10.html").read_text()
            manifest = (archive_dir / "manifest.json").read_text()

        self.assertIn('src="../js/site-config.js?v=1"', snapshot)
        self.assertIn('href="../css/digest.css?v=1"', snapshot)
        self.assertIn("2026-07-10", snapshot)
        self.assertIn('"date": "2026-07-10"', manifest)


if __name__ == "__main__":
    unittest.main()
