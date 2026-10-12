import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
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
    def test_archive_pages_resolve_runtime_fetches_from_site_root(self):
        js = CONFIG_JS.read_text()
        smoke = f"""
        const vm = require('vm');
        const ctx = {{
          window: {{ location: {{ pathname: '/market-digest/archive/2026-10-07.html' }} }},
          location: {{ hostname: 'owner.github.io' }}
        }};
        vm.runInNewContext({js!r}, ctx);
        if (ctx.mdSitePath('fred-data.json') !== '/market-digest/fred-data.json') {{
          throw new Error('archive static data path is not rooted at the site base');
        }}
        if (ctx.mdSitePath('archive/2026-10-06.html') !== '/market-digest/archive/2026-10-06.html') {{
          throw new Error('archive HTML path is not rooted at the site base');
        }}
        if (ctx.mdMacroFredUrl() !== '/market-digest/fred-data.json') {{
          throw new Error('GitHub Pages macro FRED URL is not site-rooted');
        }}
        """
        result = subprocess.run(["node", "-e", smoke], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shared_runtime_code_does_not_use_archive_relative_data_urls(self):
        charts = CHARTS_MACRO_JS.read_text()
        verdict = VERDICT_UPDATER_JS.read_text()

        self.assertIn("mdSitePath('fred-data.json')", charts)
        self.assertNotIn("loadFred('fred-data.json')", charts)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict)

    def test_sync_site_config_rewrites_externalized_archive_asset_versions(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-10-07.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20261012")

            self.assertIn('src="js/app.js?v=20261012"', (docs / "index.html").read_text())
            self.assertIn('href="css/admin.css?v=20261012"', (docs / "admin.html").read_text())
            archived = (archive / "2026-10-07.html").read_text()
            self.assertIn('src="../js/app.js?v=20261012"', archived)
            self.assertIn('href="../css/digest.css?v=20261012"', archived)


if __name__ == "__main__":
    unittest.main()
