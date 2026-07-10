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
    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        module = load_publish_digest()
        html = """
        <script src="js/site-config.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        <script src="../js/already-safe.js?v=1"></script>
        <script src="/js/root.js?v=1"></script>
        <script src="https://cdn.example/app.js"></script>
        """

        out = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', out)
        self.assertIn('href="../css/digest.css?v=1"', out)
        self.assertIn('src="../js/already-safe.js?v=1"', out)
        self.assertIn('src="/js/root.js?v=1"', out)
        self.assertIn('src="https://cdn.example/app.js"', out)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()
        current_html = """<!doctype html>
        <html><head>
        <script src="js/site-config.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        </head><body>
        <main><h1>Thursday, July 9, 2026</h1>
        <div class="meta">Summary text.</div></main>
        <script src="js/digest-init.js?v=1"></script>
        </body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_dir = root / "archive"
            archive_dir.mkdir()
            module.ARCHIVE_DIR = archive_dir
            module.MANIFEST = archive_dir / "manifest.json"

            with contextlib.redirect_stdout(io.StringIO()):
                module.archive_previous_day(current_html, "2026-07-10")

            snapshot = (archive_dir / "2026-07-09.html").read_text()
            self.assertIn('src="../js/site-config.js?v=1"', snapshot)
            self.assertIn('href="../css/digest.css?v=1"', snapshot)
            self.assertIn('src="../js/digest-init.js?v=1"', snapshot)
            self.assertIn('href="../index.html"', snapshot)

            manifest = json.loads(module.MANIFEST.read_text())
            self.assertEqual(manifest[0]["date"], "2026-07-09")


if __name__ == "__main__":
    unittest.main()
