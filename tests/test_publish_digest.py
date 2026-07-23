import importlib.util
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
    def test_archive_safe_asset_paths_rewrites_local_root_assets_only(self):
        module = load_publish_digest()
        html = """
        <script src="js/app.js?v=1"></script>
        <script src="../js/already-archive-safe.js?v=1"></script>
        <script src="https://cdn.example/app.js"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        <link href="css/print.css?v=1" rel="stylesheet">
        <link rel="stylesheet" href="../css/already-archive-safe.css?v=1">
        <link rel="stylesheet" href="https://fonts.example/css">
        """

        rewritten = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/app.js?v=1"', rewritten)
        self.assertIn('src="../js/already-archive-safe.js?v=1"', rewritten)
        self.assertIn('src="https://cdn.example/app.js"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('href="../css/print.css?v=1"', rewritten)
        self.assertIn('href="../css/already-archive-safe.css?v=1"', rewritten)
        self.assertIn('href="https://fonts.example/css"', rewritten)

    def test_archive_previous_day_writes_archive_safe_snapshot(self):
        module = load_publish_digest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_dir = root / "docs" / "archive"
            archive_dir.mkdir(parents=True)
            module.ROOT = root
            module.ARCHIVE_DIR = archive_dir
            module.MANIFEST = archive_dir / "manifest.json"
            current_html = """
            <html>
            <head>
              <script src="js/app.js?v=1"></script>
              <link rel="stylesheet" href="css/digest.css?v=1">
            </head>
            <body><main><h1>Tuesday, July 21, 2026</h1><div class="meta">Old digest.</div></main></body>
            </html>
            """

            module.archive_previous_day(current_html, "2026-07-22")

            snapshot = (archive_dir / "2026-07-21.html").read_text()
            self.assertIn('src="../js/app.js?v=1"', snapshot)
            self.assertIn('href="../css/digest.css?v=1"', snapshot)
            self.assertIn("Archived", snapshot)
            self.assertIn("2026-07-21", snapshot)


if __name__ == "__main__":
    unittest.main()
