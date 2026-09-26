import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_sync_site_config():
    script = ROOT / "scripts" / "sync_site_config.py"
    spec = importlib.util.spec_from_file_location("sync_site_config", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_config"] = module
    spec.loader.exec_module(module)
    return module


class ArchiveRuntimePathTests(unittest.TestCase):
    def run_config_helpers(self, hostname, pathname):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const root = {json.dumps(str(ROOT))};
            const context = {{
              console,
              location: {{
                hostname: {json.dumps(hostname)},
                pathname: {json.dumps(pathname)}
              }}
            }};
            context.window = context;
            vm.createContext(context);
            vm.runInContext(fs.readFileSync(root + '/docs/js/site-config.js', 'utf8'), context);
            vm.runInContext(fs.readFileSync(root + '/docs/js/config.js', 'utf8'), context);
            const out = vm.runInContext(`JSON.stringify({{
              fred: mdSitePath('fred-data.json'),
              manifest: mdSitePath('archive/manifest.json'),
              macroFred: mdMacroFredUrl()
            }})`, context);
            process.stdout.write(out);
            """
        )
        result = subprocess.run(["node", "-e", script], check=True, text=True, capture_output=True)
        return json.loads(result.stdout)

    def test_github_archive_runtime_paths_resolve_from_site_root(self):
        paths = self.run_config_helpers(
            "wesleyhu1103.github.io",
            "/market-digest/archive/2026-09-24.html",
        )

        self.assertEqual(paths["fred"], "/market-digest/fred-data.json")
        self.assertEqual(paths["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(paths["macroFred"], "/market-digest/fred-data.json")

    def test_local_archive_static_paths_resolve_from_server_root(self):
        paths = self.run_config_helpers("localhost", "/archive/2026-09-24.html")

        self.assertEqual(paths["fred"], "/fred-data.json")
        self.assertEqual(paths["manifest"], "/archive/manifest.json")
        self.assertEqual(paths["macroFred"], "/api/fred-data")

    def test_runtime_fetches_do_not_use_archive_relative_data_paths(self):
        self.assertNotIn("fetch('archive/'", (ROOT / "docs/js/verdict-updater.js").read_text())
        self.assertNotIn("loadFred('fred-data.json')", (ROOT / "docs/js/charts-macro.js").read_text())


class SyncSiteConfigTests(unittest.TestCase):
    def test_sync_html_versions_updates_archive_snapshot_asset_tags(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            docs.mkdir(exist_ok=True)
            (docs / "index.html").write_text('<script src="js/config.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-24.html").write_text(
                '<script src="../js/config.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
                '<script src="https://cdn.example/app.js?v=1"></script>'
            )

            old_root = module.ROOT
            try:
                module.ROOT = root
                module.sync_html_versions("20991231")
            finally:
                module.ROOT = old_root

            self.assertIn('src="js/config.js?v=20991231"', (docs / "index.html").read_text())
            self.assertIn('href="css/admin.css?v=20991231"', (docs / "admin.html").read_text())
            archive_html = (archive / "2026-09-24.html").read_text()
            self.assertIn('src="../js/config.js?v=20991231"', archive_html)
            self.assertIn('href="../css/digest.css?v=20991231"', archive_html)
            self.assertIn('https://cdn.example/app.js?v=1', archive_html)


if __name__ == "__main__":
    unittest.main()
