import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_sync_site_config():
    path = Path(__file__).resolve().parents[1] / "scripts" / "sync_site_config.py"
    spec = importlib.util.spec_from_file_location("sync_site_config", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SyncSiteConfigTests(unittest.TestCase):
    def test_sync_html_versions_updates_root_and_archive_asset_refs(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-08-17.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            old_root = module.ROOT
            try:
                module.ROOT = root
                module.sync_html_versions("20260818")
            finally:
                module.ROOT = old_root

            self.assertIn('src="js/app.js?v=20260818"', (docs / "index.html").read_text())
            self.assertIn('href="css/admin.css?v=20260818"', (docs / "admin.html").read_text())
            archive_html = (archive / "2026-08-17.html").read_text()
            self.assertIn('src="../js/app.js?v=20260818"', archive_html)
            self.assertIn('href="../css/digest.css?v=20260818"', archive_html)


if __name__ == "__main__":
    unittest.main()
