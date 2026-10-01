import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_config_resolves_static_assets_from_site_root_on_archive_pages(self):
        config_js = (ROOT / "docs" / "js" / "config.js").read_text()
        script = f"""
        global.MD_VERCEL_ORIGIN = 'https://market-digest.example';
        global.location = {{
          hostname: 'wesleyhu1103.github.io',
          pathname: '/market-digest/archive/2026-09-25.html'
        }};
        {config_js}
        console.log(JSON.stringify({{
          staticFred: mdMacroFredUrl(),
          archiveHtml: mdSitePath('archive/2026-09-24.html'),
          manifest: mdSitePath('archive/manifest.json')
        }}));
        """

        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )

        paths = json.loads(result.stdout)
        self.assertEqual(paths["staticFred"], "/market-digest/fred-data.json")
        self.assertEqual(paths["archiveHtml"], "/market-digest/archive/2026-09-24.html")
        self.assertEqual(paths["manifest"], "/market-digest/archive/manifest.json")

    def test_shared_runtime_uses_site_root_for_archive_fetches(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("mdSitePath(rel)", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)

    def test_sync_site_config_updates_archive_asset_versions(self):
        import importlib.util
        import sys

        script_path = ROOT / "scripts" / "sync_site_config.py"
        spec = importlib.util.spec_from_file_location("sync_site_config", script_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["sync_site_config"] = module
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "docs" / "archive"
            archive.mkdir(parents=True)
            (root / "docs" / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (root / "docs" / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            snapshot = archive / "2026-09-25.html"
            snapshot.write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )
            module.ROOT = root

            module.sync_html_versions("20260928")

            self.assertIn('src="js/app.js?v=20260928"', (root / "docs" / "index.html").read_text())
            self.assertIn('href="css/admin.css?v=20260928"', (root / "docs" / "admin.html").read_text())
            archive_html = snapshot.read_text()
            self.assertIn('src="../js/app.js?v=20260928"', archive_html)
            self.assertIn('href="../css/digest.css?v=20260928"', archive_html)


if __name__ == "__main__":
    unittest.main()
