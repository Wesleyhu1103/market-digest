import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_sync_site_config():
    script = ROOT / "scripts" / "sync_site_config.py"
    spec = importlib.util.spec_from_file_location("sync_site_config", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_archive_runtime_fetches_use_site_root_helper(self):
        config = (ROOT / "docs" / "js" / "config.js").read_text()
        archive = (ROOT / "docs" / "js" / "archive.js").read_text()
        macro = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("function mdSitePath", config)
        self.assertIn("return mdSitePath('fred-data.json')", config)
        self.assertNotIn("return 'fred-data.json'", config)

        self.assertIn("mdSitePath(rel)", archive)
        self.assertIn("sitePath('archive/manifest.json')", archive)

        self.assertIn("mdSitePath('fred-data.json')", macro)
        self.assertNotIn("loadFred('fred-data.json')", macro)

        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict)

    def test_asset_version_sync_updates_archive_relative_assets(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive_dir = docs / "archive"
            archive_dir.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive_dir / "2026-10-01.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link href="../css/digest.css?v=1" rel="stylesheet">'
            )

            module.ROOT = root
            module.ARCHIVE_DIR = archive_dir
            module.sync_html_versions("20261004")

            self.assertIn("?v=20261004", (docs / "index.html").read_text())
            self.assertIn("?v=20261004", (docs / "admin.html").read_text())
            snapshot = (archive_dir / "2026-10-01.html").read_text()
            self.assertIn('../js/app.js?v=20261004"', snapshot)
            self.assertIn('../css/digest.css?v=20261004"', snapshot)


if __name__ == "__main__":
    unittest.main()
