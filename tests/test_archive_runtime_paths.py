import importlib.util
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = ROOT / "scripts" / "sync_site_config.py"


def read_js(rel: str) -> str:
    return (ROOT / rel).read_text()


class ArchiveRuntimePathsTests(unittest.TestCase):
    def run_js(self, body: str) -> str:
        script = textwrap.dedent(body)
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def test_md_site_path_resolves_from_archive_to_site_root(self):
        js = read_js("docs/js/config.js")
        out = self.run_js(
            f"""
            global.location = {{
              hostname: 'wesleyhu1103.github.io',
              pathname: '/market-digest/archive/2026-09-28.html'
            }};
            var MD_VERCEL_ORIGIN = 'https://example.test';
            {js}
            console.log(mdSitePath('fred-data.json'));
            console.log(mdSitePath('archive/manifest.json'));
            console.log(mdMacroFredUrl());
            """
        )

        self.assertEqual(
            out.splitlines(),
            [
                "/market-digest/fred-data.json",
                "/market-digest/archive/manifest.json",
                "/market-digest/fred-data.json",
            ],
        )

    def test_runtime_scripts_use_root_path_helpers_for_archive_data(self):
        self.assertNotIn("fetch('archive/", read_js("docs/js/archive.js"))
        self.assertNotIn("fetch('archive/", read_js("docs/js/verdict-updater.js"))
        self.assertNotIn("loadFred('fred-data.json')", read_js("docs/js/charts-macro.js"))
        self.assertIn("mdSitePath('archive/", read_js("docs/js/verdict-updater.js"))
        self.assertIn("mdSitePath('fred-data.json')", read_js("docs/js/charts-macro.js"))

    def test_sync_site_config_rewrites_externalized_archive_assets(self):
        spec = importlib.util.spec_from_file_location("sync_site_config", SYNC_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules["sync_site_config"] = module
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<script src="js/admin.js?v=1"></script>')
            (archive / "2026-09-28.html").write_text(
                '<script src="../js/app.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )
            old_root = module.ROOT
            try:
                module.ROOT = root
                module.sync_html_versions("20260929")
            finally:
                module.ROOT = old_root

            self.assertIn('?v=20260929"', (docs / "index.html").read_text())
            self.assertIn('?v=20260929"', (docs / "admin.html").read_text())
            archive_html = (archive / "2026-09-28.html").read_text()
            self.assertEqual(len(re.findall(r"\\?v=20260929", archive_html)), 2)


if __name__ == "__main__":
    unittest.main()
