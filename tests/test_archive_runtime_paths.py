import importlib.util
import shutil
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


class ArchiveRuntimePathTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is required for JS helper checks")
    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        script = textwrap.dedent(
            """
            const assert = require('assert');
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync('docs/js/config.js', 'utf8');

            function resolve(path, rel) {
              const context = {
                location: { hostname: 'example.com', pathname: path },
                console,
              };
              vm.createContext(context);
              vm.runInContext(code, context);
              return vm.runInContext(`mdSitePath(${JSON.stringify(rel)})`, context);
            }

            assert.strictEqual(resolve('/archive/2026-09-17.html', 'archive/manifest.json'), '/archive/manifest.json');
            assert.strictEqual(resolve('/market-digest/archive/2026-09-17.html', 'archive/manifest.json'), '/market-digest/archive/manifest.json');
            assert.strictEqual(resolve('/market-digest/index.html', 'fred-data.json'), '/market-digest/fred-data.json');
            assert.strictEqual(resolve('/', 'fred-data.json'), '/fred-data.json');
            """
        )

        subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)

    def test_runtime_static_fetches_use_site_root_helper(self):
        js_dir = ROOT / "docs" / "js"

        for rel in ("archive.js", "charts-macro.js", "verdict-updater.js"):
            text = (js_dir / rel).read_text()
            self.assertIn("mdSitePath", text, rel)

        verdict = (js_dir / "verdict-updater.js").read_text()
        macro = (js_dir / "charts-macro.js").read_text()
        self.assertNotIn("fetch('archive/", verdict)
        self.assertNotIn('fetch("archive/', verdict)
        self.assertNotIn("loadFred('fred-data.json'", macro)
        self.assertNotIn('loadFred("fred-data.json"', macro)

    def test_sync_html_versions_updates_archive_relative_assets(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-17.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link href="../css/digest.css?v=1" rel="stylesheet">'
            )

            module.ROOT = root
            module.sync_html_versions("20260920")

            self.assertIn('src="js/app.js?v=20260920"', (docs / "index.html").read_text())
            self.assertIn('href="css/admin.css?v=20260920"', (docs / "admin.html").read_text())
            archive_html = (archive / "2026-09-17.html").read_text()
            self.assertIn('src="../js/app.js?v=20260920"', archive_html)
            self.assertIn('href="../css/digest.css?v=20260920"', archive_html)


if __name__ == "__main__":
    unittest.main()
