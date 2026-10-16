import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
SYNC_SCRIPT = ROOT / "scripts" / "sync_site_config.py"


def load_sync_site_config():
    spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class ArchiveRuntimePathTests(unittest.TestCase):
    def run_config_helper(self, pathname, hostname="wesleyhu1103.github.io"):
        script = textwrap.dedent(
            """
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync(process.argv[1], 'utf8');
            const ctx = {
              window: { location: { pathname: process.argv[2], hostname: process.argv[3] } },
              MD_VERCEL_ORIGIN: 'https://example.test'
            };
            ctx.location = ctx.window.location;
            vm.createContext(ctx);
            vm.runInContext(code, ctx);
            process.stdout.write(JSON.stringify({
              manifest: ctx.mdSitePath('archive/manifest.json'),
              fred: ctx.mdMacroFredUrl(),
              exposed: ctx.window.mdSitePath('fred-data.json')
            }));
            """
        )
        result = subprocess.run(
            ["node", "-e", script, str(CONFIG_JS), pathname, hostname],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_md_site_path_resolves_from_archive_to_site_root(self):
        paths = self.run_config_helper("/market-digest/archive/2026-10-07.html")

        self.assertEqual(paths["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(paths["fred"], "/market-digest/fred-data.json")
        self.assertEqual(paths["exposed"], "/market-digest/fred-data.json")

    def test_sync_site_config_updates_externalized_archive_cache_busts(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-10-07.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20261016")

            self.assertIn('?v=20261016"', (docs / "index.html").read_text())
            self.assertIn('?v=20261016"', (docs / "admin.html").read_text())
            archived = (archive / "2026-10-07.html").read_text()
            self.assertIn('src="../js/app.js?v=20261016"', archived)
            self.assertIn('href="../css/digest.css?v=20261016"', archived)


if __name__ == "__main__":
    unittest.main()
