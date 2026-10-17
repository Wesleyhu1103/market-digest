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


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_md_site_path_resolves_root_from_live_and_archive_pages(self):
        runner = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync({str(ROOT / 'docs' / 'js' / 'config.js')!r}, 'utf8');
            function resolve(pathname, rel) {{
              const ctx = {{
                location: {{ pathname, hostname: 'example.com' }},
                console
              }};
              vm.createContext(ctx);
              vm.runInContext(code, ctx);
              return ctx.mdSitePath(rel);
            }}
            const actual = [
              resolve('/index.html', 'fred-data.json'),
              resolve('/archive/2026-10-07.html', 'fred-data.json'),
              resolve('/market-digest/index.html', 'archive/manifest.json'),
              resolve('/market-digest/archive/2026-10-07.html', 'archive/2026-10-06.html')
            ];
            const expected = [
              '/fred-data.json',
              '/fred-data.json',
              '/market-digest/archive/manifest.json',
              '/market-digest/archive/2026-10-06.html'
            ];
            if (JSON.stringify(actual) !== JSON.stringify(expected)) {{
              console.error(JSON.stringify({{ actual, expected }}, null, 2));
              process.exit(1);
            }}
            """
        )
        subprocess.run(["node", "-e", runner], check=True)

    def test_shared_js_uses_root_aware_paths_for_archive_runtime_fetches(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_macro_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("mdSitePath(rel)", archive_js)
        self.assertIn("sitePath('archive/manifest.json')", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_macro_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)
        self.assertNotIn("fetch('archive/", archive_js + verdict_js)
        self.assertNotIn("loadFred('fred-data.json')", charts_macro_js)

    def test_sync_site_config_cache_busts_externalized_archive_snapshots(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            js = docs / "js"
            docs.mkdir()
            archive.mkdir()
            js.mkdir()
            (docs / "site-config.json").write_text(json.dumps({"assetVersion": "20261017"}))
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-10-07.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.SRC = docs / "site-config.json"
            module.OUT = js / "site-config.js"
            module.main()

            self.assertIn('?v=20261017"', (docs / "index.html").read_text())
            self.assertIn('?v=20261017"', (docs / "admin.html").read_text())
            archive_html = (archive / "2026-10-07.html").read_text()
            self.assertEqual(archive_html.count("?v=20261017"), 2)


if __name__ == "__main__":
    unittest.main()
