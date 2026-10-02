import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
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
    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        js = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync({json.dumps(str(ROOT / "docs" / "js" / "config.js"))}, 'utf8');
            const sandbox = {{
              window: {{ location: {{ pathname: '/market-digest/archive/2026-10-01.html' }} }},
              location: {{ hostname: 'wesleyhu1103.github.io' }}
            }};
            vm.createContext(sandbox);
            vm.runInContext(code, sandbox);
            process.stdout.write(JSON.stringify({{
              fred: sandbox.mdSitePath('fred-data.json'),
              archive: sandbox.mdSitePath('archive/2026-09-30.html'),
              macro: sandbox.mdMacroFredUrl()
            }}));
            """
        )

        result = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True)
        urls = json.loads(result.stdout)

        self.assertEqual(urls["fred"], "/market-digest/fred-data.json")
        self.assertEqual(urls["archive"], "/market-digest/archive/2026-09-30.html")
        self.assertEqual(urls["macro"], "/market-digest/fred-data.json")

    def test_runtime_fetches_use_site_root_helper(self):
        charts = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("mdSitePath('fred-data.json')", charts)
        self.assertNotIn("loadFred('fred-data.json')", charts)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict)

    def test_sync_site_config_updates_externalized_archive_assets(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "docs" / "archive"
            archive.mkdir(parents=True)
            (root / "docs" / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (root / "docs" / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            archive_html = archive / "2026-10-01.html"
            archive_html.write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20261002")

            self.assertIn("?v=20261002", (root / "docs" / "index.html").read_text())
            self.assertIn("?v=20261002", (root / "docs" / "admin.html").read_text())
            updated_archive = archive_html.read_text()
            self.assertIn('src="../js/app.js?v=20261002"', updated_archive)
            self.assertIn('href="../css/digest.css?v=20261002"', updated_archive)


if __name__ == "__main__":
    unittest.main()
