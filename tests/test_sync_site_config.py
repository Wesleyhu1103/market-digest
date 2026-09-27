import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_site_config.py"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class SyncSiteConfigTests(unittest.TestCase):
    def test_sync_html_versions_updates_live_and_archive_assets(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            module.ROOT = root

            (docs / "index.html").write_text(
                '<script src="js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="css/digest.css?v=1">'
            )
            (docs / "admin.html").write_text(
                '<script src="js/admin.js?v=1"></script>'
                '<script src="https://cdn.example/app.js?v=1"></script>'
            )
            (archive / "2026-09-10.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link href="../css/digest.css?v=1" rel="stylesheet">'
            )

            module.sync_html_versions("20260913")

            self.assertIn('src="js/app.js?v=20260913"', (docs / "index.html").read_text())
            self.assertIn('href="css/digest.css?v=20260913"', (docs / "index.html").read_text())
            self.assertIn('src="js/admin.js?v=20260913"', (docs / "admin.html").read_text())
            self.assertIn('src="https://cdn.example/app.js?v=1"', (docs / "admin.html").read_text())
            self.assertIn('src="../js/app.js?v=20260913"', (archive / "2026-09-10.html").read_text())
            self.assertIn('href="../css/digest.css?v=20260913"', (archive / "2026-09-10.html").read_text())


if __name__ == "__main__":
    unittest.main()
