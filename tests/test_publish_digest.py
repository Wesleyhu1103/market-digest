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
    def test_archived_snapshot_rewrites_shared_asset_paths(self):
        module = load_publish_digest()
        html = """<!doctype html>
<html><head>
<link rel="stylesheet" href="css/digest.css?v=1">
<script src="js/config.js?v=1"></script>
</head><body>
<main><header class="head"><h1>Tuesday, July 7, 2026</h1><div class="meta">old</div></header></main>
</body></html>"""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "docs" / "archive"
            archive.mkdir(parents=True)
            module.ROOT = root
            module.ARCHIVE_DIR = archive
            module.MANIFEST = archive / "manifest.json"

            module.archive_previous_day(html, "2026-07-08")

            snapshot = (archive / "2026-07-07.html").read_text()
            self.assertIn('href="../css/digest.css?v=1"', snapshot)
            self.assertIn('src="../js/config.js?v=1"', snapshot)
            self.assertIn('href="../index.html"', snapshot)
            manifest = json.loads(module.MANIFEST.read_text())
            self.assertEqual(manifest[0]["date"], "2026-07-07")


if __name__ == "__main__":
    unittest.main()
