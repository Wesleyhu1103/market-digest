import importlib.util
import json
import shutil
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


class StaticAssetPathTests(unittest.TestCase):
    def test_md_site_path_resolves_from_archive_to_site_root(self):
        if not shutil.which("node"):
            self.skipTest("Node.js is required to evaluate shared browser helpers")

        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8');

            function evaluate(pathname, hostname) {{
              const ctx = {{
                location: {{ pathname, hostname }},
                MD_VERCEL_ORIGIN: 'https://market-digest-liart.vercel.app'
              }};
              vm.createContext(ctx);
              vm.runInContext(code, ctx);
              return {{
                siteFred: ctx.mdSitePath('fred-data.json'),
                macroFred: ctx.mdMacroFredUrl()
              }};
            }}

            const results = [
              evaluate('/market-digest/archive/2026-09-18.html', 'wesleyhu1103.github.io'),
              evaluate('/market-digest/', 'wesleyhu1103.github.io'),
              evaluate('/archive/2026-09-18.html', 'market-digest-liart.vercel.app')
            ];
            console.log(JSON.stringify(results));
            """
        )
        out = subprocess.check_output(["node", "-e", script], text=True)
        results = json.loads(out)

        self.assertEqual(results[0]["siteFred"], "/market-digest/fred-data.json")
        self.assertEqual(results[0]["macroFred"], "/market-digest/fred-data.json")
        self.assertEqual(results[1]["siteFred"], "/market-digest/fred-data.json")
        self.assertEqual(results[2]["siteFred"], "/fred-data.json")
        self.assertEqual(results[2]["macroFred"], "/api/fred-data")

    def test_shared_js_uses_site_root_for_archive_runtime_fetches(self):
        config = CONFIG_JS.read_text()
        archive = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("function mdSitePath(path)", config)
        self.assertIn("return mdSitePath('fred-data.json')", config)
        self.assertIn("return mdSitePath(rel)", archive)
        self.assertIn("loadFred(mdSitePath('fred-data.json'))", charts)
        self.assertIn("fetch(mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertNotIn("loadFred('fred-data.json')", charts)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict)

    def test_sync_site_config_updates_externalized_archive_versions(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<script src="js/site-config.js?v=1"></script>')
            (archive / "2026-09-18.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20260921")

            self.assertIn('?v=20260921"', (docs / "index.html").read_text())
            self.assertIn('?v=20260921"', (docs / "admin.html").read_text())
            snapshot = (archive / "2026-09-18.html").read_text()
            self.assertIn('src="../js/app.js?v=20260921"', snapshot)
            self.assertIn('href="../css/digest.css?v=20260921"', snapshot)


if __name__ == "__main__":
    unittest.main()
