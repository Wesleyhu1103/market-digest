import importlib.util
import json
import subprocess
import sys
import tempfile
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
    def eval_config(self, pathname, hostname="wesleyhu1103.github.io"):
        config = (ROOT / "docs" / "js" / "config.js").read_text()
        script = (
            f"var location = {json.dumps({'hostname': hostname, 'pathname': pathname})};\n"
            "var MD_VERCEL_ORIGIN = 'https://example.test';\n"
            f"{config}\n"
            "console.log(JSON.stringify({\n"
            "  manifest: mdSitePath('archive/manifest.json'),\n"
            "  fred: mdSitePath('fred-data.json'),\n"
            "  macroFred: mdMacroFredUrl()\n"
            "}));\n"
        )
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        resolved = self.eval_config("/archive/2026-09-24.html")

        self.assertEqual(resolved["manifest"], "/archive/manifest.json")
        self.assertEqual(resolved["fred"], "/fred-data.json")
        self.assertEqual(resolved["macroFred"], "/fred-data.json")

    def test_md_site_path_preserves_repo_base_on_github_pages(self):
        resolved = self.eval_config("/market-digest/archive/2026-09-24.html")

        self.assertEqual(resolved["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(resolved["fred"], "/market-digest/fred-data.json")
        self.assertEqual(resolved["macroFred"], "/market-digest/fred-data.json")

    def test_archive_runtime_fetches_do_not_use_archive_relative_urls(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        macro_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("mdSitePath", archive_js)
        self.assertNotIn("loadFred('fred-data.json')", macro_js)
        self.assertNotIn("fetch('archive/'", verdict_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)


class SyncSiteConfigArchiveTests(unittest.TestCase):
    def test_sync_html_versions_updates_externalized_archive_assets(self):
        module = load_sync_site_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            archive.mkdir(parents=True)
            (docs / "index.html").write_text('<script src="js/app.js?v=1"></script>')
            (docs / "admin.html").write_text('<script src="js/admin.js?v=1"></script>')
            (archive / "2026-09-24.html").write_text(
                '<script src="../js/app.js?v=1"></script>\n'
                '<link rel="stylesheet" href="../css/digest.css?v=1">\n'
                '<script src="https://cdn.example/app.js?v=1"></script>'
            )

            module.ROOT = root
            module.sync_html_versions("999")

            self.assertIn('src="js/app.js?v=999"', (docs / "index.html").read_text())
            self.assertIn('src="js/admin.js?v=999"', (docs / "admin.html").read_text())
            archived = (archive / "2026-09-24.html").read_text()
            self.assertIn('src="../js/app.js?v=999"', archived)
            self.assertIn('href="../css/digest.css?v=999"', archived)
            self.assertIn('src="https://cdn.example/app.js?v=1"', archived)


if __name__ == "__main__":
    unittest.main()
