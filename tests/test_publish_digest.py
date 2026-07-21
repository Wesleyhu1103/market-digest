import importlib.util
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
        html = (
            '<script src="js/app.js?v=1"></script>'
            '<link rel="stylesheet" href="css/site.css?v=1">'
            '<link href="css/print.css?v=1" rel="stylesheet">'
            '<script src="../js/archive-ok.js?v=1"></script>'
            '<script src="https://cdn.example/app.js"></script>'
        )

        out = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/app.js?v=1"', out)
        self.assertIn('href="../css/site.css?v=1"', out)
        self.assertIn('href="../css/print.css?v=1"', out)
        self.assertIn('src="../js/archive-ok.js?v=1"', out)
        self.assertIn('src="https://cdn.example/app.js"', out)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()
        current_html = """<!doctype html>
<html><head>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head><body><main><header class="head"><h1>Friday, July 17, 2026</h1><div class="meta">Old edition.</div></header></main>
<script src="js/digest-init.js?v=1"></script></body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            archive_dir = Path(tmp) / "archive"
            archive_dir.mkdir()
            module.ARCHIVE_DIR = archive_dir
            module.MANIFEST = archive_dir / "manifest.json"
            module.ROOT = Path(tmp)

            module.archive_previous_day(current_html, "2026-07-18")

            snapshot = (archive_dir / "2026-07-17.html").read_text()
            manifest = json.loads((archive_dir / "manifest.json").read_text())

        self.assertIn('src="../js/site-config.js?v=1"', snapshot)
        self.assertIn('href="../css/digest.css?v=1"', snapshot)
        self.assertIn('src="../js/digest-init.js?v=1"', snapshot)
        self.assertEqual(manifest[0]["date"], "2026-07-17")


if __name__ == "__main__":
    unittest.main()
