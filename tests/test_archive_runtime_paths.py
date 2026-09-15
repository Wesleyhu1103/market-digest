import json
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRuntimePathTests(unittest.TestCase):
    def eval_config_paths(self, pathname, hostname="example.github.io"):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const location = {{ hostname: {json.dumps(hostname)}, pathname: {json.dumps(pathname)} }};
            const context = {{
              window: {{ location }},
              location,
              MD_VERCEL_ORIGIN: 'https://market-digest.example',
              console
            }};
            vm.createContext(context);
            vm.runInContext(fs.readFileSync('docs/js/config.js', 'utf8'), context);
            const out = {{
              fred: vm.runInContext("mdSitePath('fred-data.json')", context),
              manifest: vm.runInContext("mdSitePath('archive/manifest.json')", context),
              macro: vm.runInContext("mdMacroFredUrl()", context)
            }};
            console.log(JSON.stringify(out));
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_site_path_resolves_from_archive_to_site_root(self):
        paths = self.eval_config_paths("/market-digest/archive/2026-09-14.html")

        self.assertEqual(paths["fred"], "/market-digest/fred-data.json")
        self.assertEqual(paths["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(paths["macro"], "/market-digest/fred-data.json")

    def test_site_path_keeps_live_page_base(self):
        paths = self.eval_config_paths("/market-digest/")

        self.assertEqual(paths["fred"], "/market-digest/fred-data.json")
        self.assertEqual(paths["manifest"], "/market-digest/archive/manifest.json")

    def test_runtime_fetches_use_archive_safe_helpers(self):
        archive_js = (ROOT / "docs/js/archive.js").read_text()
        charts_macro_js = (ROOT / "docs/js/charts-macro.js").read_text()
        verdict_js = (ROOT / "docs/js/verdict-updater.js").read_text()

        self.assertNotIn("loadFred('fred-data.json')", charts_macro_js)
        self.assertNotIn("fetch('archive/", verdict_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_macro_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)
        self.assertIn("mdSitePath(rel)", archive_js)


if __name__ == "__main__":
    unittest.main()
