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


class StaticSitePathTests(unittest.TestCase):
    def node_eval(self, body: str) -> str:
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const assert = require('assert');
            global.MD_VERCEL_ORIGIN = 'https://market-digest-liart.vercel.app';
            {body}
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_site_paths_resolve_from_archive_page_to_site_root(self):
        body = f"""
        global.location = {{
          hostname: 'wesleyhu1103.github.io',
          pathname: '/market-digest/archive/2026-08-21.html'
        }};
        eval(fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8'));
        assert.strictEqual(mdSitePath('fred-data.json'), '/market-digest/fred-data.json');
        assert.strictEqual(
          mdSitePath('archive/2026-08-20.html'),
          '/market-digest/archive/2026-08-20.html'
        );
        assert.strictEqual(mdMacroFredUrl(), '/market-digest/fred-data.json');
        console.log('ok');
        """

        self.assertEqual(self.node_eval(body), "ok")

    def test_site_paths_resolve_from_live_index_to_site_root(self):
        body = f"""
        global.location = {{
          hostname: 'wesleyhu1103.github.io',
          pathname: '/market-digest/index.html'
        }};
        eval(fs.readFileSync({json.dumps(str(CONFIG_JS))}, 'utf8'));
        assert.strictEqual(mdSitePath('archive/manifest.json'), '/market-digest/archive/manifest.json');
        assert.strictEqual(mdMacroFredUrl(), '/market-digest/fred-data.json');
        console.log('ok');
        """

        self.assertEqual(self.node_eval(body), "ok")

    def test_runtime_fetches_do_not_use_archive_relative_literals(self):
        snippets = "\n".join(
            (ROOT / rel).read_text()
            for rel in (
                "docs/js/archive.js",
                "docs/js/charts-macro.js",
                "docs/js/config.js",
                "docs/js/verdict-updater.js",
            )
        )

        self.assertNotIn("fetch('archive/", snippets)
        self.assertNotIn('fetch("archive/', snippets)
        self.assertNotIn("loadFred('fred-data.json')", snippets)
        self.assertNotIn('loadFred("fred-data.json")', snippets)
        self.assertNotIn("return 'fred-data.json'", snippets)
        self.assertNotIn('return "fred-data.json"', snippets)

    def test_published_archives_do_not_keep_legacy_relative_runtime_paths(self):
        snippets = "\n".join(path.read_text() for path in (ROOT / "docs" / "archive").glob("*.html"))

        self.assertNotIn("fetch('archive/manifest.json'", snippets)
        self.assertNotIn('fetch("archive/manifest.json', snippets)
        self.assertNotIn("return 'fred-data.json'", snippets)
        self.assertNotIn('return "fred-data.json"', snippets)
        self.assertNotIn('href="\' + e.url + \'"', snippets)
        self.assertNotIn(
            "function sitePath(rel) {\n"
            "      var path = window.location.pathname || '/';\n"
            "      if (/\\.[a-z0-9]+$/i.test(path))",
            snippets,
        )

    def test_sync_html_versions_updates_archive_asset_tags(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<script src="js/site-config.js?v=1"></script>')
            (archive / "2026-08-21.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )
            module.ROOT = root

            module.sync_html_versions("20260824")

            self.assertIn('src="js/app.js?v=20260824"', (docs / "index.html").read_text())
            self.assertIn(
                'src="../js/app.js?v=20260824"',
                (archive / "2026-08-21.html").read_text(),
            )
            self.assertIn(
                'href="../css/digest.css?v=20260824"',
                (archive / "2026-08-21.html").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
