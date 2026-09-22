import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_DIR = ROOT / "docs" / "js"


class StaticRuntimePathTests(unittest.TestCase):
    def test_shared_js_keeps_root_aware_site_path_helper(self):
        config_js = (JS_DIR / "config.js").read_text()

        self.assertIn("function mdSitePath(", config_js)
        self.assertIn("path.indexOf('/archive/')", config_js)
        self.assertIn("return mdSiteBasePath() +", config_js)

    def test_site_path_helper_resolves_from_site_root_on_archives(self):
        script = r"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('docs/js/config.js', 'utf8');
function resolve(path, rel) {
  const ctx = {
    location: { hostname: 'wesleyhu1103.github.io', pathname: path },
    MD_VERCEL_ORIGIN: 'https://market-digest.example',
    console
  };
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  return ctx.mdSitePath(rel);
}
const actual = [
  resolve('/market-digest/index.html', 'fred-data.json'),
  resolve('/market-digest/archive/2026-09-21.html', 'fred-data.json'),
  resolve('/archive/2026-09-21.html', 'archive/manifest.json')
];
const expected = [
  '/market-digest/fred-data.json',
  '/market-digest/fred-data.json',
  '/archive/manifest.json'
];
if (JSON.stringify(actual) !== JSON.stringify(expected)) {
  console.error(JSON.stringify({ actual, expected }));
  process.exit(1);
}
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_shared_js_has_no_archive_relative_data_fetches(self):
        bundle = "\n".join(path.read_text() for path in JS_DIR.glob("*.js"))

        stale_patterns = [
            r"fetch\(['\"]archive/",
            r"loadFred\(['\"]fred-data\.json",
            r"return\s+['\"]fred-data\.json",
        ]
        for pattern in stale_patterns:
            self.assertIsNone(re.search(pattern, bundle), pattern)


if __name__ == "__main__":
    unittest.main()
