import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        script = r"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('docs/js/config.js', 'utf8');

function evaluate(pathname, hostname, rel) {
  const ctx = { location: { pathname, hostname }, window: {} };
  vm.createContext(ctx);
  vm.runInContext(code + `
    result = mdSitePath(${JSON.stringify(rel)});
    fred = mdMacroFredUrl();
  `, ctx);
  return { path: ctx.result, fred: ctx.fred };
}

console.log(JSON.stringify({
  archived: evaluate('/market-digest/archive/2026-10-07.html', 'wesleyhu1103.github.io', 'archive/manifest.json'),
  live: evaluate('/market-digest/index.html', 'wesleyhu1103.github.io', 'archive/manifest.json')
}));
"""
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        values = json.loads(result.stdout)

        self.assertEqual(values["archived"]["path"], "/market-digest/archive/manifest.json")
        self.assertEqual(values["archived"]["fred"], "/market-digest/fred-data.json")
        self.assertEqual(values["live"]["path"], "/market-digest/archive/manifest.json")
        self.assertEqual(values["live"]["fred"], "/market-digest/fred-data.json")

    def test_shared_js_avoids_archive_relative_runtime_fetches(self):
        charts = (ROOT / "docs/js/charts-macro.js").read_text()
        verdict = (ROOT / "docs/js/verdict-updater.js").read_text()
        archive = (ROOT / "docs/js/archive.js").read_text()

        self.assertNotIn("loadFred('fred-data.json')", charts)
        self.assertNotIn("fetch('archive/", verdict)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertIn("typeof mdSitePath === 'function'", archive)


if __name__ == "__main__":
    unittest.main()
