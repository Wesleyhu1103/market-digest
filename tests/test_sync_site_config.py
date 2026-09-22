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
    def test_sync_html_versions_updates_live_admin_and_archive_assets(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text(
                '<script src="js/config.js?v=1"></script>\n'
                '<link rel="stylesheet" href="css/digest.css?v=1">\n'
                '<script src="https://cdn.example/app.js?v=1"></script>\n'
            )
            (docs / "admin.html").write_text(
                '<script src="js/site-config.js?v=1"></script>\n'
            )
            (archive / "2026-08-18.html").write_text(
                '<script src="../js/config.js?v=1"></script>\n'
                '<link rel="stylesheet" href="../css/digest.css?v=1">\n'
            )

            module.ROOT = root
            module.sync_html_versions("20260819")

            self.assertIn('js/config.js?v=20260819', (docs / "index.html").read_text())
            self.assertIn('css/digest.css?v=20260819', (docs / "index.html").read_text())
            self.assertIn("cdn.example/app.js?v=1", (docs / "index.html").read_text())
            self.assertIn('js/site-config.js?v=20260819', (docs / "admin.html").read_text())
            snapshot = (archive / "2026-08-18.html").read_text()
            self.assertIn('../js/config.js?v=20260819', snapshot)
            self.assertIn('../css/digest.css?v=20260819', snapshot)


if __name__ == "__main__":
    unittest.main()
