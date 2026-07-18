import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_digest.py"


def load_publish_digest():
    spec = importlib.util.spec_from_file_location("publish_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublishDigestTests(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_root_assets_only(self):
        module = load_publish_digest()
        html = """
        <script src="js/app.js?v=1"></script>
        <script src="../js/already-safe.js?v=1"></script>
        <script src="https://cdn.example/app.js"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        <link href="css/late.css?v=1" rel="stylesheet">
        <link rel="preconnect" href="css/not-a-stylesheet.css">
        """

        rewritten = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/app.js?v=1"', rewritten)
        self.assertIn('src="../js/already-safe.js?v=1"', rewritten)
        self.assertIn('src="https://cdn.example/app.js"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('href="../css/late.css?v=1"', rewritten)
        self.assertIn('href="css/not-a-stylesheet.css"', rewritten)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()
        html = """<!doctype html>
        <html><head>
        <title>Market Digest</title>
        <script src="js/app.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        </head><body>
        <main><h1>Thursday, July 16, 2026</h1><div class="meta">Summary</div></main>
        </body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_dir = root / "docs" / "archive"
            archive_dir.mkdir(parents=True)
            module.ROOT = root
            module.ARCHIVE_DIR = archive_dir
            module.MANIFEST = archive_dir / "manifest.json"

            with contextlib.redirect_stdout(io.StringIO()):
                module.archive_previous_day(html, "2026-07-17")

            snapshot = (archive_dir / "2026-07-16.html").read_text()
            self.assertIn('src="../js/app.js?v=1"', snapshot)
            self.assertIn('href="../css/digest.css?v=1"', snapshot)
            manifest = json.loads(module.MANIFEST.read_text())
            self.assertEqual(manifest[0]["date"], "2026-07-16")


if __name__ == "__main__":
    unittest.main()
