import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_digest.py"


def load_publish_digest():
    spec = importlib.util.spec_from_file_location("publish_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["publish_digest"] = module
    spec.loader.exec_module(module)
    return module


class PublishDigestTests(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        module = load_publish_digest()
        html = (
            '<script src="js/app.js?v=1"></script>'
            '<link href="css/digest.css?v=1">'
            '<script src="https://cdn.example/chart.js"></script>'
            '<a href="archive/2026-07-08.html">Archive</a>'
        )

        out = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/app.js?v=1"', out)
        self.assertIn('href="../css/digest.css?v=1"', out)
        self.assertIn('src="https://cdn.example/chart.js"', out)
        self.assertIn('href="archive/2026-07-08.html"', out)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()
        current_html = """<!doctype html>
<html><head>
<script src="js/site-config.js?v=1"></script>
<link href="css/digest.css?v=1" rel="stylesheet">
</head><body><main>
<header class="head"><h1>Wednesday, July 8, 2026</h1><div class="meta"><p>Old digest summary.</p></div></header>
</main></body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_dir = root / "docs" / "archive"
            archive_dir.mkdir(parents=True)
            module.ROOT = root
            module.ARCHIVE_DIR = archive_dir
            module.MANIFEST = archive_dir / "manifest.json"

            module.archive_previous_day(current_html, "2026-07-09")

            snapshot = archive_dir / "2026-07-08.html"
            self.assertTrue(snapshot.exists())
            html = snapshot.read_text()
            self.assertIn('src="../js/site-config.js?v=1"', html)
            self.assertIn('href="../css/digest.css?v=1"', html)
            self.assertIn("Archived — 2026-07-08", html)

            manifest = json.loads(module.MANIFEST.read_text())
            self.assertEqual(manifest[0]["date"], "2026-07-08")
            self.assertEqual(manifest[0]["url"], "archive/2026-07-08.html")


if __name__ == "__main__":
    unittest.main()
