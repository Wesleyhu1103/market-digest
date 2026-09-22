import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = ROOT / "scripts" / "sync_site_config.py"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class StaticAssetPathTests(unittest.TestCase):
    def test_config_site_paths_resolve_from_archive_to_site_root(self):
        script = r"""
        const fs = require('fs');
        const vm = require('vm');
        const code = fs.readFileSync('docs/js/config.js', 'utf8');

        function evaluate(hostname, pathname) {
          const storage = {};
          const sandbox = {
            location: { hostname, pathname },
            MD_VERCEL_ORIGIN: 'https://example.vercel.app',
            crypto: { randomUUID: () => 'uuid' },
            localStorage: {
              getItem: (key) => storage[key] || null,
              setItem: (key, value) => { storage[key] = String(value); }
            },
            fetch: () => Promise.resolve({ ok: true })
          };
          vm.createContext(sandbox);
          vm.runInContext(code, sandbox);
          return {
            fred: sandbox.mdSitePath('fred-data.json'),
            manifest: sandbox.mdSitePath('/archive/manifest.json'),
            macro: sandbox.mdMacroFredUrl()
          };
        }

        console.log(JSON.stringify({
          archive: evaluate('wesleyhu1103.github.io', '/market-digest/archive/2026-08-14.html'),
          live: evaluate('wesleyhu1103.github.io', '/market-digest/'),
          localArchive: evaluate('localhost', '/archive/2026-08-14.html')
        }));
        """
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        data = json.loads(result.stdout)

        self.assertEqual(data["archive"]["fred"], "/market-digest/fred-data.json")
        self.assertEqual(data["archive"]["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(data["archive"]["macro"], "/market-digest/fred-data.json")
        self.assertEqual(data["live"]["fred"], "/market-digest/fred-data.json")
        self.assertEqual(data["localArchive"]["fred"], "/fred-data.json")
        self.assertEqual(data["localArchive"]["macro"], "/api/fred-data")

    def test_archive_and_macro_scripts_use_root_safe_helpers(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()

        self.assertIn("archivePath('archive/manifest.json')", archive_js)
        self.assertIn("archivePath(e.url || '')", archive_js)
        self.assertNotIn("fetch(sitePath('archive/manifest.json')", archive_js)
        self.assertIn("function staticFredUrl()", charts_js)
        self.assertIn("return loadFred(fallback).then", charts_js)

    def test_sync_site_config_rewrites_archive_asset_versions(self):
        module = load_sync_site_config()
        html = """
        <script src="../js/config.js?v=20260724"></script>
        <script src="js/config.js?v=20260724"></script>
        <link rel="stylesheet" href="../css/digest.css?v=20260724">
        <script src="https://cdn.example/app.js?v=1"></script>
        """

        rewritten, count = module.ASSET_TAG_RE.subn(r'\1?v=20260817"', html)

        self.assertEqual(count, 3)
        self.assertIn('src="../js/config.js?v=20260817"', rewritten)
        self.assertIn('src="js/config.js?v=20260817"', rewritten)
        self.assertIn('href="../css/digest.css?v=20260817"', rewritten)
        self.assertIn('src="https://cdn.example/app.js?v=1"', rewritten)

    def test_archive_snapshots_do_not_fetch_data_from_archive_directory(self):
        bad_patterns = (
            "fetch('fred-data.json'",
            'fetch("fred-data.json"',
            "loadFred('fred-data.json'",
            'loadFred("fred-data.json"',
            "return 'fred-data.json'",
            'return "fred-data.json"',
            "fetch('archive/manifest.json'",
            'fetch("archive/manifest.json"',
        )
        offenders = []
        for path in sorted((ROOT / "docs" / "archive").glob("2026-*.html")):
            text = path.read_text(errors="ignore")
            for pattern in bad_patterns:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
