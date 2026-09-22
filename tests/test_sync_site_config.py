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
                '<script src="js/archive.js?v=1"></script>'
                '<link rel="stylesheet" href="css/digest.css?v=1">'
            )
            (docs / "admin.html").write_text('<script src="js/site-config.js?v=1"></script>')
            (archive / "2026-08-25.html").write_text(
                '<script src="../js/archive.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
                '<script src="https://cdn.example/app.js?v=1"></script>'
            )

            module.ROOT = root
            module.sync_html_versions("20260827")

            self.assertIn("js/archive.js?v=20260827", (docs / "index.html").read_text())
            self.assertIn("js/site-config.js?v=20260827", (docs / "admin.html").read_text())
            archived = (archive / "2026-08-25.html").read_text()
            self.assertIn("../js/archive.js?v=20260827", archived)
            self.assertIn("../css/digest.css?v=20260827", archived)
            self.assertIn("https://cdn.example/app.js?v=1", archived)


if __name__ == "__main__":
    unittest.main()
