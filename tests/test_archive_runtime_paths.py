import importlib.util
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
    def test_md_site_path_resolves_from_site_root_inside_archive_pages(self):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            global.window = {{ location: {{
              pathname: '/market-digest/archive/2026-08-28.html',
              hostname: 'wesleyhu1103.github.io'
            }} }};
            global.location = window.location;
            eval(fs.readFileSync({str(CONFIG_JS)!r}, 'utf8'));
            if (mdSitePath('archive/manifest.json') !== '/market-digest/archive/manifest.json') process.exit(1);
            if (mdSitePath('fred-data.json') !== '/market-digest/fred-data.json') process.exit(2);
            if (mdMacroFredUrl() !== '/market-digest/fred-data.json') process.exit(3);
            """
        )

        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_fetches_do_not_use_archive_relative_static_paths(self):
        forbidden = {
            "docs/js/verdict-updater.js": "fetch('archive/",
            "docs/js/charts-macro.js": "loadFred('fred-data.json'",
            "docs/js/config.js": "return 'fred-data.json'",
        }

        for rel, needle in forbidden.items():
            with self.subTest(rel=rel):
                self.assertNotIn(needle, (ROOT / rel).read_text())

    def test_sync_site_config_updates_archive_snapshot_asset_versions(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<script src="js/site-config.js?v=1"></script>')
            archived = archive / "2026-08-28.html"
            archived.write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20990101")

            self.assertIn('src="js/app.js?v=20990101"', (docs / "index.html").read_text())
            self.assertIn('src="js/site-config.js?v=20990101"', (docs / "admin.html").read_text())
            archived_text = archived.read_text()
            self.assertIn('src="../js/app.js?v=20990101"', archived_text)
            self.assertIn('href="../css/digest.css?v=20990101"', archived_text)


if __name__ == "__main__":
    unittest.main()
