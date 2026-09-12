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


class StaticSitePathTests(unittest.TestCase):
    def test_shared_js_uses_site_root_for_archive_sensitive_fetches(self):
        checks = {
            "docs/js/archive.js": ["fetch('archive/manifest.json", 'fetch("archive/manifest.json'],
            "docs/js/charts-macro.js": ["loadFred('fred-data.json", 'loadFred("fred-data.json'],
            "docs/js/verdict-updater.js": ["fetch('archive/'", 'fetch("archive/"'],
        }
        for rel, bad_needles in checks.items():
            text = (ROOT / rel).read_text()
            for needle in bad_needles:
                self.assertNotIn(needle, text, f"{rel} should route {needle} through mdSitePath()")

    def test_sync_versions_updates_archive_asset_tags(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link href="css/admin.css?v=1" rel="stylesheet">')
            archived = archive / "2026-09-10.html"
            archived.write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20260912")

            self.assertIn("js/app.js?v=20260912", (docs / "index.html").read_text())
            self.assertIn("css/admin.css?v=20260912", (docs / "admin.html").read_text())
            archived_text = archived.read_text()
            self.assertIn("../js/app.js?v=20260912", archived_text)
            self.assertIn("../css/digest.css?v=20260912", archived_text)


if __name__ == "__main__":
    unittest.main()
