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
    def test_shared_js_avoids_archive_relative_runtime_fetches(self):
        shared_js = "\n".join((ROOT / "docs" / "js" / name).read_text() for name in [
            "archive.js",
            "charts-macro.js",
            "verdict-updater.js",
        ])

        self.assertNotRegex(shared_js, r"fetch\(\s*['\"]archive/")
        self.assertNotRegex(shared_js, r"fetch\(\s*['\"]fred-data\.json")
        self.assertNotRegex(shared_js, r"loadFred\(\s*['\"]fred-data\.json")

    def test_md_site_path_resolves_from_site_root_on_archive_pages(self):
        cases = [
            {
                "hostname": "wesleyhu1103.github.io",
                "pathname": "/market-digest/archive/2026-09-29.html",
                "rel": "fred-data.json",
                "expected": "/market-digest/fred-data.json",
                "fred": "/market-digest/fred-data.json",
            },
            {
                "hostname": "wesleyhu1103.github.io",
                "pathname": "/market-digest/index.html",
                "rel": "archive/manifest.json",
                "expected": "/market-digest/archive/manifest.json",
                "fred": "/market-digest/fred-data.json",
            },
            {
                "hostname": "market-digest-liart.vercel.app",
                "pathname": "/archive/2026-09-29.html",
                "rel": "archive/2026-09-28.html",
                "expected": "/archive/2026-09-28.html",
                "fred": "/api/fred-data",
            },
        ]
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8');
            const cases = {json.dumps(cases)};
            const out = cases.map((c) => {{
              const ctx = {{
                location: {{ hostname: c.hostname, pathname: c.pathname }},
                MD_VERCEL_ORIGIN: 'https://market-digest-liart.vercel.app'
              }};
              vm.runInNewContext(source, ctx);
              return {{
                site: ctx.mdSitePath(c.rel),
                fred: ctx.mdMacroFredUrl()
              }};
            }});
            console.log(JSON.stringify(out));
            """
        )

        result = subprocess.run(["node", "-e", script], check=True, text=True, capture_output=True)
        actual = json.loads(result.stdout)

        self.assertEqual([item["site"] for item in actual], [case["expected"] for case in cases])
        self.assertEqual([item["fred"] for item in actual], [case["fred"] for case in cases])

    def test_sync_site_config_updates_archive_asset_versions(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-29.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
                '<script src="https://cdn.example/app.js?v=1"></script>'
            )
            module.ROOT = root

            module.sync_html_versions("20260930")

            self.assertIn('src="js/app.js?v=20260930"', (docs / "index.html").read_text())
            self.assertIn('href="css/admin.css?v=20260930"', (docs / "admin.html").read_text())
            archived = (archive / "2026-09-29.html").read_text()
            self.assertIn('src="../js/app.js?v=20260930"', archived)
            self.assertIn('href="../css/digest.css?v=20260930"', archived)
            self.assertIn('src="https://cdn.example/app.js?v=1"', archived)


if __name__ == "__main__":
    unittest.main()
