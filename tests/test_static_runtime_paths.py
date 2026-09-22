import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticRuntimePathTests(unittest.TestCase):
    def test_site_path_resolves_assets_from_site_root_on_archive_pages(self):
        script = r"""
const fs = require('fs');
const vm = require('vm');

function inspect(hostname, pathname) {
  const ctx = {
    location: { hostname, pathname },
    MD_VERCEL_ORIGIN: 'https://market-digest.example',
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync('docs/js/config.js', 'utf8'), ctx);
  return {
    fred: ctx.mdSitePath('fred-data.json'),
    manifest: ctx.mdSitePath('archive/manifest.json'),
    press: ctx.mdSitePath('archive/2026-08-27.html'),
    macroFred: ctx.mdMacroFredUrl(),
  };
}

const githubArchive = inspect('wesleyhu1103.github.io', '/market-digest/archive/2026-08-27.html');
const vercelArchive = inspect('market-digest-liart.vercel.app', '/archive/2026-08-27.html');
console.log(JSON.stringify({ githubArchive, vercelArchive }));
"""
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)

        self.assertEqual(data["githubArchive"]["fred"], "/market-digest/fred-data.json")
        self.assertEqual(data["githubArchive"]["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(data["githubArchive"]["press"], "/market-digest/archive/2026-08-27.html")
        self.assertEqual(data["githubArchive"]["macroFred"], "/market-digest/fred-data.json")
        self.assertEqual(data["vercelArchive"]["fred"], "/fred-data.json")
        self.assertEqual(data["vercelArchive"]["macroFred"], "/api/fred-data")

    def test_runtime_fetches_do_not_use_archive_relative_literals(self):
        combined = "\n".join(
            (ROOT / rel).read_text()
            for rel in (
                "docs/js/archive.js",
                "docs/js/charts-macro.js",
                "docs/js/verdict-updater.js",
            )
        )

        self.assertNotRegex(combined, r"(fetch|loadFred)\(\s*['\"](?:archive/|fred-data\.json)")


if __name__ == "__main__":
    unittest.main()
