import importlib.util
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
        html = """<head>
<script src="js/site-config.js?v=1"></script>
<script src="../js/already-safe.js?v=1"></script>
<script src="https://example.test/app.js"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
<link rel="stylesheet" href="../css/already-safe.css?v=1">
<link rel="preconnect" href="https://fonts.example">
</head>"""

        rewritten = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', rewritten)
        self.assertIn('src="../js/already-safe.js?v=1"', rewritten)
        self.assertIn('src="https://example.test/app.js"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('href="../css/already-safe.css?v=1"', rewritten)
        self.assertIn('href="https://fonts.example"', rewritten)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()
        current_html = """<!doctype html>
<html><head>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head><body><main>
<header><h1>Monday, July 13, 2026</h1><div class="meta">Yesterday</div></header>
</main></body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            module.ARCHIVE_DIR = Path(tmp) / "archive"
            module.ARCHIVE_DIR.mkdir()
            module.MANIFEST = module.ARCHIVE_DIR / "manifest.json"

            module.archive_previous_day(current_html, "2026-07-14")

            snapshot = (module.ARCHIVE_DIR / "2026-07-13.html").read_text()
            self.assertIn('src="../js/site-config.js?v=1"', snapshot)
            self.assertIn('href="../css/digest.css?v=1"', snapshot)
            self.assertIn("Archived — 2026-07-13", snapshot)


if __name__ == "__main__":
    unittest.main()
