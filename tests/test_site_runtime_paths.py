import importlib.util
import json
import subprocess
import sys
import tempfile
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


class SiteRuntimePathTests(unittest.TestCase):
    def test_md_site_path_resolves_from_archive_pages_to_site_root(self):
        script = textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            const src = fs.readFileSync('docs/js/config.js', 'utf8');

            function inspect(pathname, hostname) {
              const ctx = {
                location: { pathname, hostname },
                fetch: () => Promise.resolve({ ok: true }),
                console
              };
              vm.createContext(ctx);
              vm.runInContext(src + `
                this.result = {
                  manifest: mdSitePath('archive/manifest.json'),
                  fred: mdMacroFredUrl()
                };
              `, ctx);
              return ctx.result;
            }

            console.log(JSON.stringify({
              live: inspect('/index.html', 'example.github.io'),
              archive: inspect('/archive/2026-09-15.html', 'example.github.io'),
              projectArchive: inspect('/market-digest/archive/2026-09-15.html', 'example.github.io'),
              vercelArchive: inspect('/archive/2026-09-15.html', 'market-digest-liart.vercel.app')
            }));
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        paths = json.loads(result.stdout)

        self.assertEqual(paths["live"]["manifest"], "/archive/manifest.json")
        self.assertEqual(paths["archive"]["manifest"], "/archive/manifest.json")
        self.assertEqual(paths["archive"]["fred"], "/fred-data.json")
        self.assertEqual(paths["projectArchive"]["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(paths["projectArchive"]["fred"], "/market-digest/fred-data.json")
        self.assertEqual(paths["vercelArchive"]["fred"], "/api/fred-data")

    def test_shared_scripts_use_site_root_for_archive_data_reads(self):
        checks = {
            ROOT / "docs" / "js" / "archive.js": "mdSitePath('archive/manifest.json')",
            ROOT / "docs" / "js" / "charts-macro.js": "mdSitePath('fred-data.json')",
            ROOT / "docs" / "js" / "verdict-updater.js": "mdSitePath('archive/' + iso + '.html')",
        }
        for path, needle in checks.items():
            with self.subTest(path=path.name):
                self.assertIn(needle, path.read_text())

    def test_sync_site_config_updates_archive_asset_versions(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "js").mkdir()
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link href="css/admin.css?v=1" rel="stylesheet">')
            (archive / "2026-09-15.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
                '<script src="https://cdn.example/app.js?v=1"></script>'
            )

            module.ROOT = root
            module.sync_html_versions("20260916")

            self.assertIn('?v=20260916"', (docs / "index.html").read_text())
            self.assertIn('?v=20260916"', (docs / "admin.html").read_text())
            archive_html = (archive / "2026-09-15.html").read_text()
            self.assertIn('src="../js/app.js?v=20260916"', archive_html)
            self.assertIn('href="../css/digest.css?v=20260916"', archive_html)
            self.assertIn('src="https://cdn.example/app.js?v=1"', archive_html)


if __name__ == "__main__":
    unittest.main()
