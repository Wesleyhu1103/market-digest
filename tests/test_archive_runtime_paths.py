import json
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
CHARTS_MACRO_JS = ROOT / "docs" / "js" / "charts-macro.js"
VERDICT_UPDATER_JS = ROOT / "docs" / "js" / "verdict-updater.js"


def eval_config(pathname, hostname="wesleyhu1103.github.io"):
    script = textwrap.dedent(
        f"""
        const fs = require('fs');
        const vm = require('vm');
        const ctx = {{
          location: {{ hostname: {json.dumps(hostname)}, pathname: {json.dumps(pathname)} }},
          MD_VERCEL_ORIGIN: 'https://market-digest.example',
          window: {{}}
        }};
        ctx.window = ctx;
        vm.createContext(ctx);
        vm.runInContext(fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8'), ctx);
        process.stdout.write(JSON.stringify({{
          archiveManifest: ctx.mdSitePath('archive/manifest.json'),
          fredData: ctx.mdSitePath('fred-data.json'),
          macroFred: ctx.mdMacroFredUrl()
        }}));
        """
    )
    result = subprocess.run(["node", "-e", script], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_site_path_resolves_from_live_page_root(self):
        data = eval_config("/market-digest/index.html")

        self.assertEqual(data["archiveManifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(data["fredData"], "/market-digest/fred-data.json")

    def test_site_path_resolves_from_archive_page_root(self):
        data = eval_config("/market-digest/archive/2026-09-18.html")

        self.assertEqual(data["archiveManifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(data["fredData"], "/market-digest/fred-data.json")
        self.assertEqual(data["macroFred"], "/market-digest/fred-data.json")

    def test_macro_uses_api_on_vercel_archive_pages(self):
        data = eval_config("/archive/2026-09-18.html", hostname="market-digest-liart.vercel.app")

        self.assertEqual(data["archiveManifest"], "/archive/manifest.json")
        self.assertEqual(data["fredData"], "/fred-data.json")
        self.assertEqual(data["macroFred"], "/api/fred-data")

    def test_shared_js_does_not_fetch_archive_relative_data_directly(self):
        macro = CHARTS_MACRO_JS.read_text()
        verdict = VERDICT_UPDATER_JS.read_text()

        self.assertNotIn("loadFred('fred-data.json')", macro)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict)


if __name__ == "__main__":
    unittest.main()
