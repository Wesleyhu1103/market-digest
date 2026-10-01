import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
ARCHIVE_JS = ROOT / "docs" / "js" / "archive.js"
CHARTS_MACRO_JS = ROOT / "docs" / "js" / "charts-macro.js"
VERDICT_UPDATER_JS = ROOT / "docs" / "js" / "verdict-updater.js"
SYNC_SCRIPT = ROOT / "scripts" / "sync_site_config.py"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_runtime_data_fetches_use_site_root_helper(self):
        config_js = CONFIG_JS.read_text()
        archive_js = ARCHIVE_JS.read_text()
        charts_macro_js = CHARTS_MACRO_JS.read_text()
        verdict_updater_js = VERDICT_UPDATER_JS.read_text()

        self.assertIn("function mdSitePath(rel)", config_js)
        self.assertIn("path.indexOf('/archive/')", config_js)
        self.assertIn("return mdSitePath('fred-data.json')", config_js)

        self.assertIn("if (typeof mdSitePath === 'function') return mdSitePath(rel);", archive_js)
        self.assertIn("sitePath('archive/manifest.json')", archive_js)
        self.assertIn("sitePath(e.url || '')", archive_js)

        self.assertIn("mdSitePath('fred-data.json')", charts_macro_js)
        self.assertNotIn("loadFred('fred-data.json')", charts_macro_js)

        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_updater_js)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict_updater_js)

    def test_asset_sync_updates_externalized_archive_snapshots(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-30.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            old_root = module.ROOT
            try:
                module.ROOT = root
                module.sync_html_versions("20261001")
            finally:
                module.ROOT = old_root

            self.assertIn("?v=20261001", (docs / "index.html").read_text())
            self.assertIn("?v=20261001", (docs / "admin.html").read_text())
            snapshot = (archive / "2026-09-30.html").read_text()
            self.assertIn('src="../js/app.js?v=20261001"', snapshot)
            self.assertIn('href="../css/digest.css?v=20261001"', snapshot)


if __name__ == "__main__":
    unittest.main()
