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
    def run_config_js(self, pathname, hostname, expr):
        script = textwrap.dedent(
            f"""
            global.location = {{ pathname: {pathname!r}, hostname: {hostname!r} }};
            global.MD_VERCEL_ORIGIN = 'https://example.vercel.app';
            {CONFIG_JS.read_text()}
            process.stdout.write(String({expr}));
            """
        )
        result = subprocess.run(["node", "-e", script], check=True, text=True, capture_output=True)
        return result.stdout

    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        self.assertEqual(
            self.run_config_js("/archive/2026-09-29.html", "market-digest-liart.vercel.app", "mdSitePath('fred-data.json')"),
            "/fred-data.json",
        )
        self.assertEqual(
            self.run_config_js("/market-digest/archive/2026-09-29.html", "wesleyhu1103.github.io", "mdSitePath('archive/2026-09-28.html')"),
            "/market-digest/archive/2026-09-28.html",
        )

    def test_github_pages_static_fred_uses_site_root(self):
        self.assertEqual(
            self.run_config_js("/market-digest/archive/2026-09-29.html", "wesleyhu1103.github.io", "mdMacroFredUrl()"),
            "/market-digest/fred-data.json",
        )

    def test_no_archive_relative_runtime_fetches_remain(self):
        self.assertNotIn("fetch('archive/", (ROOT / "docs" / "js" / "verdict-updater.js").read_text())
        self.assertNotIn('fetch("archive/', (ROOT / "docs" / "js" / "verdict-updater.js").read_text())
        self.assertNotIn("loadFred('fred-data.json')", (ROOT / "docs" / "js" / "charts-macro.js").read_text())

    def test_sync_site_config_updates_archive_cache_bust_tags(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<link rel="stylesheet" href="css/admin.css?v=1">')
            (archive / "2026-09-29.html").write_text(
                '<script src="../js/app.js?v=1"></script><link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            module.ROOT = root
            module.sync_html_versions("20260930")

            self.assertIn("?v=20260930", (docs / "index.html").read_text())
            self.assertIn("?v=20260930", (docs / "admin.html").read_text())
            self.assertEqual((archive / "2026-09-29.html").read_text().count("?v=20260930"), 2)


if __name__ == "__main__":
    unittest.main()
