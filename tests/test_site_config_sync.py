import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SYNC_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_site_config.py"
CONFIG_JS = Path(__file__).resolve().parents[1] / "docs" / "js" / "config.js"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class SiteConfigSyncTests(unittest.TestCase):
    def test_md_site_path_resolves_from_archive_to_site_root(self):
        script = CONFIG_JS.read_text()
        runner = f"""
        var MD_VERCEL_ORIGIN = 'https://example.test';
        var location = {{ hostname: 'wesleyhu1103.github.io', pathname: '/market-digest/archive/2026-09-11.html' }};
        {script}
        console.log(mdSitePath('archive/manifest.json'));
        console.log(mdSitePath('fred-data.json'));
        console.log(mdMacroFredUrl());
        """
        result = subprocess.run(["node", "-e", runner], capture_output=True, text=True, check=True)

        self.assertEqual(
            result.stdout.strip().splitlines(),
            [
                "/market-digest/archive/manifest.json",
                "/market-digest/fred-data.json",
                "/market-digest/fred-data.json",
            ],
        )

    def test_shared_js_avoids_archive_relative_data_fetches(self):
        js = "\n".join(
            (Path(__file__).resolve().parents[1] / rel).read_text()
            for rel in [
                "docs/js/archive.js",
                "docs/js/charts-macro.js",
                "docs/js/verdict-updater.js",
            ]
        )

        self.assertNotRegex(js, r"fetch\(['\"]archive/")
        self.assertNotRegex(js, r"loadFred\(['\"]fred-data\.json")

    def test_sync_html_versions_updates_archive_safe_asset_refs(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-11.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
                '<script src="https://cdn.example/app.js?v=1"></script>'
            )

            old_root = module.ROOT
            module.ROOT = root
            try:
                module.sync_html_versions("20260914")
            finally:
                module.ROOT = old_root

            self.assertIn('?v=20260914"', (docs / "index.html").read_text())
            self.assertIn('?v=20260914"', (docs / "admin.html").read_text())
            archived = (archive / "2026-09-11.html").read_text()
            self.assertIn('src="../js/app.js?v=20260914"', archived)
            self.assertIn('href="../css/digest.css?v=20260914"', archived)
            self.assertIn('src="https://cdn.example/app.js?v=1"', archived)


if __name__ == "__main__":
    unittest.main()
