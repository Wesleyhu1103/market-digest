import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_digest.py"


def load_publish_digest():
    import sys

    spec = importlib.util.spec_from_file_location("publish_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["publish_digest"] = module
    spec.loader.exec_module(module)
    return module


class PublishDigestTests(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        module = load_publish_digest()

        html = (
            '<script src="js/site-config.js?v=1"></script>\n'
            '<link rel="stylesheet" href="css/digest.css?v=1">\n'
            '<script src="../js/already-safe.js?v=1"></script>\n'
            '<script src="https://example.com/js/app.js"></script>'
        )

        rewritten = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('src="../js/already-safe.js?v=1"', rewritten)
        self.assertIn('src="https://example.com/js/app.js"', rewritten)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()

        current_html = """<!doctype html>
<html><head>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head><body>
<main>
<h1>Thursday, July 09, 2026</h1>
<div class="meta">Market summary</div>
</main>
<script src="js/digest-init.js?v=1"></script>
</body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module.ROOT = root
            module.ARCHIVE_DIR = root / "docs" / "archive"
            module.MANIFEST = module.ARCHIVE_DIR / "manifest.json"
            module.ARCHIVE_DIR.mkdir(parents=True)

            module.archive_previous_day(current_html, "2026-07-10")

            snapshot = (module.ARCHIVE_DIR / "2026-07-09.html").read_text()
            self.assertIn('src="../js/site-config.js?v=1"', snapshot)
            self.assertIn('href="../css/digest.css?v=1"', snapshot)
            self.assertIn('src="../js/digest-init.js?v=1"', snapshot)
            self.assertNotIn('src="js/', snapshot)
            self.assertNotIn('href="css/', snapshot)

            manifest = json.loads(module.MANIFEST.read_text())
            self.assertEqual(manifest[0]["date"], "2026-07-09")


if __name__ == "__main__":
    unittest.main()
