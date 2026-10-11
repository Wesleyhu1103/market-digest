import json
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
ARCHIVE_JS = ROOT / "docs" / "js" / "archive.js"
CHARTS_MACRO_JS = ROOT / "docs" / "js" / "charts-macro.js"
VERDICT_UPDATER_JS = ROOT / "docs" / "js" / "verdict-updater.js"


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_md_site_path_resolves_from_archive_to_site_root(self):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8');

            function contextFor(pathname, hostname) {{
              const location = {{ pathname, hostname }};
              const context = {{ location, window: {{ location }}, console }};
              vm.createContext(context);
              vm.runInContext(code, context);
              return context;
            }}

            const outputs = [
              contextFor('/market-digest/index.html', 'wesleyhu1103.github.io').mdSitePath('archive/manifest.json'),
              contextFor('/market-digest/archive/2026-10-07.html', 'wesleyhu1103.github.io').mdSitePath('archive/manifest.json'),
              contextFor('/archive/2026-10-07.html', 'market-digest-liart.vercel.app').mdSitePath('fred-data.json'),
              contextFor('/market-digest', 'wesleyhu1103.github.io').mdMacroFredUrl(),
              contextFor('/market-digest/archive/2026-10-07.html', 'wesleyhu1103.github.io').mdMacroFredUrl(),
              contextFor('/archive/2026-10-07.html', 'market-digest-liart.vercel.app').mdMacroFredUrl()
            ];
            console.log(JSON.stringify(outputs));
            """
        )
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)

        self.assertEqual(
            json.loads(result.stdout),
            [
                "/market-digest/archive/manifest.json",
                "/market-digest/archive/manifest.json",
                "/fred-data.json",
                "/market-digest/fred-data.json",
                "/market-digest/fred-data.json",
                "/api/fred-data",
            ],
        )

    def test_archive_sensitive_fetches_use_site_root_helper(self):
        archive_js = ARCHIVE_JS.read_text()
        charts_macro_js = CHARTS_MACRO_JS.read_text()
        verdict_updater_js = VERDICT_UPDATER_JS.read_text()

        self.assertIn("return mdSitePath(rel)", archive_js)
        self.assertIn("sitePath('archive/manifest.json')", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_macro_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_updater_js)
        self.assertNotIn("loadFred('fred-data.json')", charts_macro_js)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict_updater_js)


if __name__ == "__main__":
    unittest.main()
