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


class StaticRuntimePathTests(unittest.TestCase):
    def test_config_exposes_root_aware_site_paths(self):
        text = CONFIG_JS.read_text()

        self.assertIn("function mdSiteBasePath()", text)
        self.assertIn("function mdSitePath(rel)", text)
        self.assertIn("path.indexOf('/archive/')", text)
        self.assertIn("return mdSitePath('fred-data.json');", text)
        self.assertNotIn("return 'fred-data.json';", text)

    def test_shared_scripts_do_not_fetch_archive_relative_data(self):
        archive_js = ARCHIVE_JS.read_text()
        charts_js = CHARTS_MACRO_JS.read_text()
        verdict_js = VERDICT_UPDATER_JS.read_text()

        self.assertIn("mdSitePath(rel)", archive_js)
        self.assertIn("sitePath('archive/manifest.json')", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_js)
        self.assertNotIn("loadFred('fred-data.json')", charts_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict_js)

    def test_archives_do_not_fetch_nested_archive_paths(self):
        for path in (ROOT / "docs" / "archive").glob("*.html"):
            text = path.read_text()
            self.assertNotIn("fetch('archive/manifest.json'", text, path.name)
            self.assertNotIn('fetch("archive/manifest.json"', text, path.name)
            self.assertNotIn("fetch('fred-data.json'", text, path.name)
            self.assertNotIn('fetch("fred-data.json"', text, path.name)
            self.assertNotIn('href="\' + e.url + \'"', text, path.name)

    def test_sync_site_config_updates_archive_asset_versions(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<script src="js/site-config.js?v=1"></script>')
            (archive / "2026-08-26.html").write_text(
                '<script src="../js/app.js?v=1"></script><link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20260827")

            self.assertIn('src="js/app.js?v=20260827"', (docs / "index.html").read_text())
            self.assertIn('src="js/site-config.js?v=20260827"', (docs / "admin.html").read_text())
            archive_text = (archive / "2026-08-26.html").read_text()
            self.assertIn('src="../js/app.js?v=20260827"', archive_text)
            self.assertIn('href="../css/digest.css?v=20260827"', archive_text)


if __name__ == "__main__":
    unittest.main()
