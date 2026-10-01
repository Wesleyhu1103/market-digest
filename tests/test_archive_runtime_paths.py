import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
SYNC_SCRIPT = ROOT / "scripts" / "sync_site_config.py"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_site_path_resolves_archive_pages_to_site_root(self):
        node_script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const assert = require('assert');
            const code = fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8');

            function run(pathname, hostname) {{
              const sandbox = {{ location: {{ pathname, hostname }} }};
              vm.createContext(sandbox);
              vm.runInContext(code, sandbox);
              return {{
                fred: sandbox.mdSitePath('fred-data.json'),
                macro: sandbox.mdMacroFredUrl()
              }};
            }}

            assert.deepStrictEqual(
              run('/market-digest/archive/2026-09-28.html', 'wesleyhu1103.github.io'),
              {{ fred: '/market-digest/fred-data.json', macro: '/market-digest/fred-data.json' }}
            );
            assert.deepStrictEqual(
              run('/market-digest/index.html', 'wesleyhu1103.github.io'),
              {{ fred: '/market-digest/fred-data.json', macro: '/market-digest/fred-data.json' }}
            );
            assert.deepStrictEqual(
              run('/archive/2026-09-28.html', 'market-digest-liart.vercel.app'),
              {{ fred: '/fred-data.json', macro: '/api/fred-data' }}
            );
            """
        )
        subprocess.run(["node", "-e", node_script], check=True)

    def test_runtime_fetches_use_site_root_helper(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_macro_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("mdSitePath(rel)", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_macro_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict_js)

    def test_sync_site_config_updates_externalized_archives(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-28.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )
            module.ROOT = root

            module.sync_html_versions("20260929")

            self.assertIn('?v=20260929"', (docs / "index.html").read_text())
            self.assertIn('?v=20260929"', (docs / "admin.html").read_text())
            archive_html = (archive / "2026-09-28.html").read_text()
            self.assertIn('../js/app.js?v=20260929"', archive_html)
            self.assertIn('../css/digest.css?v=20260929"', archive_html)


if __name__ == "__main__":
    unittest.main()
