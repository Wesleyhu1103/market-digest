import json
import importlib.util
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StaticUrlHelperTests(unittest.TestCase):
    @unittest.skipIf(shutil.which("node") is None, "node is required for JS helper checks")
    def test_site_paths_resolve_from_root_on_live_and_archive_pages(self):
        script = textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            const src = fs.readFileSync(process.argv[1], 'utf8');

            function run(hostname, pathname) {
              const context = {
                window: { location: { hostname, pathname } },
                location: { hostname, pathname },
                MD_VERCEL_ORIGIN: 'https://api.example.test'
              };
              vm.createContext(context);
              vm.runInContext(src, context);
              return {
                manifest: context.mdSitePath('archive/manifest.json'),
                archive: context.mdSitePath('archive/2026-09-15.html'),
                fred: context.mdSitePath('fred-data.json'),
                macroFred: context.mdMacroFredUrl()
              };
            }

            console.log(JSON.stringify({
              ghLive: run('wesleyhu1103.github.io', '/market-digest/'),
              ghArchive: run('wesleyhu1103.github.io', '/market-digest/archive/2026-09-15.html'),
              customArchive: run('market-digest-liart.vercel.app', '/archive/2026-09-15.html')
            }));
            """
        )
        result = subprocess.run(
            ["node", "-e", script, str(ROOT / "docs" / "js" / "config.js")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)

        self.assertEqual(data["ghLive"]["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(data["ghLive"]["fred"], "/market-digest/fred-data.json")
        self.assertEqual(data["ghLive"]["macroFred"], "/market-digest/fred-data.json")

        self.assertEqual(data["ghArchive"]["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(data["ghArchive"]["archive"], "/market-digest/archive/2026-09-15.html")
        self.assertEqual(data["ghArchive"]["fred"], "/market-digest/fred-data.json")
        self.assertEqual(data["ghArchive"]["macroFred"], "/market-digest/fred-data.json")

        self.assertEqual(data["customArchive"]["manifest"], "/archive/manifest.json")
        self.assertEqual(data["customArchive"]["archive"], "/archive/2026-09-15.html")
        self.assertEqual(data["customArchive"]["fred"], "/fred-data.json")
        self.assertEqual(data["customArchive"]["macroFred"], "/api/fred-data")

    def test_asset_sync_regex_matches_archive_relative_tags(self):
        module = load_script_module("sync_site_config", ROOT / "scripts" / "sync_site_config.py")
        html = (
            '<script src="../js/config.js?v=20260724"></script>\n'
            '<link rel="stylesheet" href="../css/digest.css?v=20260724">\n'
            '<script src="https://cdn.example/app.js?v=20260724"></script>\n'
        )

        updated, count = module.ASSET_TAG_RE.subn(r'\1?v=20260916"', html)

        self.assertEqual(count, 2)
        self.assertIn('src="../js/config.js?v=20260916"', updated)
        self.assertIn('href="../css/digest.css?v=20260916"', updated)
        self.assertIn('https://cdn.example/app.js?v=20260724', updated)


if __name__ == "__main__":
    unittest.main()
