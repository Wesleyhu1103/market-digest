import importlib.util
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
ARCHIVE_JS = ROOT / "docs" / "js" / "archive.js"
CHARTS_MACRO_JS = ROOT / "docs" / "js" / "charts-macro.js"
VERDICT_JS = ROOT / "docs" / "js" / "verdict-updater.js"
DIGEST_INIT_JS = ROOT / "docs" / "js" / "digest-init.js"
SYNC_SCRIPT = ROOT / "scripts" / "sync_site_config.py"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class RuntimePathTests(unittest.TestCase):
    def test_md_site_path_resolves_archive_pages_from_site_root(self):
        js = textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync(process.argv[1], 'utf8');
            const ctx = {
              window: {
                location: {
                  pathname: '/market-digest/archive/2026-08-27.html',
                  hostname: 'wesleyhu1103.github.io'
                }
              },
              location: {
                pathname: '/market-digest/archive/2026-08-27.html',
                hostname: 'wesleyhu1103.github.io'
              },
              MD_VERCEL_ORIGIN: 'https://example.test',
              console
            };
            vm.createContext(ctx);
            vm.runInContext(code, ctx);
            const out = {
              manifest: ctx.mdSitePath('archive/manifest.json'),
              fred: ctx.mdMacroFredUrl(),
              archive: ctx.mdSitePath('archive/2026-08-26.html'),
              absolute: ctx.mdSitePath('https://cdn.example/app.js')
            };
            console.log(JSON.stringify(out));
            """
        )
        proc = subprocess.run(
            ["node", "-e", js, str(CONFIG_JS)],
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            proc.stdout.strip(),
            '{"manifest":"/market-digest/archive/manifest.json",'
            '"fred":"/market-digest/fred-data.json",'
            '"archive":"/market-digest/archive/2026-08-26.html",'
            '"absolute":"https://cdn.example/app.js"}',
        )

    def test_archive_runtime_consumers_use_root_aware_helpers(self):
        self.assertIn("mdSitePath(rel)", ARCHIVE_JS.read_text())
        self.assertIn("mdSitePath('fred-data.json')", CHARTS_MACRO_JS.read_text())
        self.assertIn("mdSitePath('archive/' + iso + '.html')", VERDICT_JS.read_text())
        self.assertIn("mdScoreboardAnchorIso", VERDICT_JS.read_text())
        self.assertIn("mdScoreboardAnchorIso", DIGEST_INIT_JS.read_text())

    def test_sync_site_config_updates_archive_snapshot_asset_versions(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link href="css/admin.css?v=1" rel="stylesheet">')
            (archive / "2026-08-27.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )
            module.ROOT = root

            module.sync_html_versions("20260829")

            self.assertIn('?v=20260829"', (docs / "index.html").read_text())
            self.assertIn('?v=20260829"', (docs / "admin.html").read_text())
            archive_text = (archive / "2026-08-27.html").read_text()
            self.assertEqual(archive_text.count("?v=20260829"), 2)


if __name__ == "__main__":
    unittest.main()
