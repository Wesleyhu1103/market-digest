import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"


class StaticRuntimePathTests(unittest.TestCase):
    def eval_config(self, hostname, pathname, expression):
        script = f"""
const fs = require('fs');
const vm = require('vm');
const ctx = {{
  location: {{ hostname: {json.dumps(hostname)}, pathname: {json.dumps(pathname)} }},
  console,
  localStorage: {{ getItem() {{ return null; }}, setItem() {{}} }},
  crypto: {{ randomUUID() {{ return 'test-id'; }} }}
}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8'), ctx);
process.stdout.write(vm.runInContext({json.dumps(expression)}, ctx));
"""
        proc = subprocess.run(["node", "-e", script], text=True, capture_output=True, check=True)
        return proc.stdout

    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        result = self.eval_config(
            "wesleyhu1103.github.io",
            "/market-digest/archive/2026-08-25.html",
            "JSON.stringify([mdSitePath('fred-data.json'), mdSitePath('archive/manifest.json'), mdMacroFredUrl()])",
        )

        self.assertEqual(
            json.loads(result),
            [
                "/market-digest/fred-data.json",
                "/market-digest/archive/manifest.json",
                "/market-digest/fred-data.json",
            ],
        )

    def test_archive_runtime_fetches_use_site_root_helper(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("return mdSitePath(rel)", archive_js)
        self.assertIn("sitePath('archive/manifest.json')", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict_js)
        self.assertNotIn("loadFred('fred-data.json')", charts_js)


if __name__ == "__main__":
    unittest.main()
