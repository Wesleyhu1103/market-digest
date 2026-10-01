import importlib.util
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


class StaticRuntimePathTests(unittest.TestCase):
    def test_md_site_path_resolves_from_live_and_archive_pages(self):
        config_js = ROOT / "docs" / "js" / "config.js"
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync({str(config_js)!r}, 'utf8');
            function run(pathname, hostname) {{
              const context = {{
                location: {{ pathname, hostname }},
                MD_VERCEL_ORIGIN: 'https://market-digest-liart.vercel.app'
              }};
              vm.createContext(context);
              vm.runInContext(code, context);
              return {{
                manifest: context.mdSitePath('archive/manifest.json'),
                fred: context.mdSitePath('fred-data.json'),
                macro: context.mdMacroFredUrl()
              }};
            }}
            const live = run('/market-digest/index.html', 'wesleyhu1103.github.io');
            const archive = run('/market-digest/archive/2026-09-21.html', 'wesleyhu1103.github.io');
            const vercelArchive = run('/archive/2026-09-21.html', 'market-digest-liart.vercel.app');
            if (live.manifest !== '/market-digest/archive/manifest.json') throw new Error('bad live manifest ' + live.manifest);
            if (archive.manifest !== '/market-digest/archive/manifest.json') throw new Error('bad archive manifest ' + archive.manifest);
            if (archive.fred !== '/market-digest/fred-data.json') throw new Error('bad archive fred ' + archive.fred);
            if (archive.macro !== '/market-digest/fred-data.json') throw new Error('bad github macro ' + archive.macro);
            if (vercelArchive.manifest !== '/archive/manifest.json') throw new Error('bad vercel archive manifest ' + vercelArchive.manifest);
            if (vercelArchive.macro !== '/api/fred-data') throw new Error('bad vercel macro ' + vercelArchive.macro);
            """
        )
        subprocess.run(["node", "-e", script], check=True)

    def test_runtime_js_uses_site_root_for_archive_relative_fetches(self):
        self.assertNotIn("loadFred('fred-data.json')", (ROOT / "docs" / "js" / "charts-macro.js").read_text())
        self.assertNotIn("fetch('archive/'", (ROOT / "docs" / "js" / "verdict-updater.js").read_text())

    def test_sync_html_versions_updates_archive_snapshots(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-21.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            old_root = module.ROOT
            try:
                module.ROOT = root
                module.sync_html_versions("20260922")
            finally:
                module.ROOT = old_root

            self.assertIn('?v=20260922"', (docs / "index.html").read_text())
            self.assertIn('?v=20260922"', (docs / "admin.html").read_text())
            snapshot = (archive / "2026-09-21.html").read_text()
            self.assertIn('src="../js/app.js?v=20260922"', snapshot)
            self.assertIn('href="../css/digest.css?v=20260922"', snapshot)


if __name__ == "__main__":
    unittest.main()
