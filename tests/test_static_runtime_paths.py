import importlib.util
import json
import subprocess
import sys
import textwrap
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


class StaticRuntimePathTests(unittest.TestCase):
    def run_node_json(self, script: str):
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        script = textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            const ctx = {
              console,
              window: { location: { pathname: '/market-digest/archive/2026-09-23.html', hostname: 'example.github.io' } },
              MD_VERCEL_ORIGIN: 'https://market-digest.example'
            };
            ctx.location = ctx.window.location;
            vm.createContext(ctx);
            vm.runInContext(fs.readFileSync('docs/js/config.js', 'utf8'), ctx);
            console.log(JSON.stringify({
              manifest: ctx.mdSitePath('archive/manifest.json'),
              fred: ctx.mdSitePath('fred-data.json'),
              macroFred: ctx.mdMacroFredUrl()
            }));
            """
        )

        data = self.run_node_json(script)

        self.assertEqual(data["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(data["fred"], "/market-digest/fred-data.json")
        self.assertEqual(data["macroFred"], "/market-digest/fred-data.json")

    def test_archive_manifest_fetch_uses_site_root_from_archive_page(self):
        script = textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            const calls = [];
            const mount = { innerHTML: '' };
            const ctx = {
              console,
              window: { location: { pathname: '/archive/2026-09-23.html', hostname: 'market-digest.example' }, DigestDate: null },
              MD_VERCEL_ORIGIN: 'https://market-digest.example',
              document: {
                getElementById(id) { return id === 'archive-mount' ? mount : null; },
                querySelector() { return null; },
                createElement() { return { innerHTML: '', appendChild() {} }; },
                body: { appendChild() {} }
              },
              fetch(url) {
                calls.push(url);
                return Promise.resolve({
                  ok: true,
                  json: () => Promise.resolve([
                    { date: '2026-09-23', h1: 'Wednesday, September 23, 2026', summary: 'Archived issue', url: 'archive/2026-09-23.html' }
                  ])
                });
              }
            };
            ctx.location = ctx.window.location;
            vm.createContext(ctx);
            vm.runInContext(fs.readFileSync('docs/js/config.js', 'utf8'), ctx);
            vm.runInContext(fs.readFileSync('docs/js/archive.js', 'utf8'), ctx);
            setImmediate(() => setImmediate(() => {
              console.log(JSON.stringify({ calls, html: mount.innerHTML }));
            }));
            """
        )

        data = self.run_node_json(script)

        self.assertEqual(data["calls"][0], "/archive/manifest.json")
        self.assertIn('href="/archive/2026-09-23.html"', data["html"])

    def test_sync_site_config_updates_archive_safe_asset_tags(self):
        module = load_sync_site_config()
        html = """
        <script src="js/app.js?v=1"></script>
        <script src="../js/archive-app.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        <link rel="stylesheet" href="../css/archive.css?v=1">
        <script src="https://cdn.example/app.js?v=1"></script>
        """

        updated = module.ASSET_TAG_RE.sub(r'\1?v=20260924"', html)

        self.assertIn('src="js/app.js?v=20260924"', updated)
        self.assertIn('src="../js/archive-app.js?v=20260924"', updated)
        self.assertIn('href="css/digest.css?v=20260924"', updated)
        self.assertIn('href="../css/archive.css?v=20260924"', updated)
        self.assertIn('src="https://cdn.example/app.js?v=1"', updated)

    def test_no_archive_relative_runtime_data_fetch_literals(self):
        self.assertNotIn("fetch('archive/'", (ROOT / "docs/js/verdict-updater.js").read_text())
        self.assertNotIn("loadFred('fred-data.json')", (ROOT / "docs/js/charts-macro.js").read_text())


if __name__ == "__main__":
    unittest.main()
