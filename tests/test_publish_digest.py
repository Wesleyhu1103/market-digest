import contextlib
import importlib.util
import io
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
    def test_archive_safe_asset_paths_rewrites_root_local_assets_only(self):
        module = load_publish_digest()
        html = """
        <script src="js/site-config.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        <script src="../js/already-archive-safe.js?v=1"></script>
        <script src="https://cdn.example.com/lib.js"></script>
        <a href="js/not-an-asset.js">source</a>
        """

        rewritten = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('src="../js/already-archive-safe.js?v=1"', rewritten)
        self.assertIn('src="https://cdn.example.com/lib.js"', rewritten)
        self.assertIn('href="js/not-an-asset.js"', rewritten)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()
        current_html = """<!doctype html>
<html><head>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head><body><main>
<header class="head"><h1>Wednesday, July 15, 2026</h1>
<div class="meta"><p>Prior digest summary.</p></div></header>
</main></body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_dir = root / "docs" / "archive"
            archive_dir.mkdir(parents=True)
            module.ROOT = root
            module.ARCHIVE_DIR = archive_dir
            module.MANIFEST = archive_dir / "manifest.json"

            with contextlib.redirect_stdout(io.StringIO()):
                module.archive_previous_day(current_html, "2026-07-16")

            snapshot = (archive_dir / "2026-07-15.html").read_text()
            self.assertIn('src="../js/site-config.js?v=1"', snapshot)
            self.assertIn('href="../css/digest.css?v=1"', snapshot)
            self.assertIn("Archived", snapshot)


if __name__ == "__main__":
    unittest.main()
