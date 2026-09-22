import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = ROOT / "scripts" / "sync_site_config.py"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class StaticRuntimePathTests(unittest.TestCase):
    def test_archive_sensitive_fetches_use_root_aware_site_paths(self):
        config = (ROOT / "docs" / "js" / "config.js").read_text()
        archive = (ROOT / "docs" / "js" / "archive.js").read_text()
        macro = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("function mdSiteBasePath()", config)
        self.assertIn("path.indexOf('/archive/')", config)
        self.assertIn("function mdSitePath(path)", config)
        self.assertIn("mdSitePath('fred-data.json')", config)
        self.assertIn("mdSitePath(rel)", archive)
        self.assertIn("mdSitePath('fred-data.json')", macro)
        self.assertNotIn("loadFred('fred-data.json')", macro)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict)

    def test_asset_sync_updates_externalized_archive_snapshots(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            docs.mkdir(exist_ok=True)
            (docs / "index.html").write_text('<script src="js/config.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-10.html").write_text(
                '<script src="../js/config.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20260911")

            self.assertIn("?v=20260911", (docs / "index.html").read_text())
            self.assertIn("?v=20260911", (docs / "admin.html").read_text())
            archive_html = (archive / "2026-09-10.html").read_text()
            self.assertIn('../js/config.js?v=20260911"', archive_html)
            self.assertIn('../css/digest.css?v=20260911"', archive_html)


if __name__ == "__main__":
    unittest.main()
