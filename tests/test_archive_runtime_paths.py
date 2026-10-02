import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRuntimePathsTest(unittest.TestCase):
    def test_md_site_path_resolves_archive_pages_to_site_root(self):
        script = f"""
        global.location = {{ pathname: '/market-digest/archive/2026-10-01.html', hostname: 'wesleyhu1103.github.io' }};
        eval(require('fs').readFileSync({str(ROOT / 'docs/js/config.js')!r}, 'utf8'));
        if (mdSitePath('fred-data.json') !== '../fred-data.json') process.exit(1);
        if (mdSitePath('archive/manifest.json') !== '../archive/manifest.json') process.exit(2);
        if (mdMacroFredUrl() !== '../fred-data.json') process.exit(3);
        global.location = {{ pathname: '/market-digest/index.html', hostname: 'wesleyhu1103.github.io' }};
        if (mdSitePath('fred-data.json') !== 'fred-data.json') process.exit(4);
        """

        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shared_archive_fetches_use_site_root_helper(self):
        archive_js = (ROOT / "docs/js/archive.js").read_text()
        charts_macro = (ROOT / "docs/js/charts-macro.js").read_text()
        verdict_updater = (ROOT / "docs/js/verdict-updater.js").read_text()

        self.assertIn("mdSitePath(rel)", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_macro)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_updater)
        self.assertNotIn("fetch('archive/", verdict_updater)
        self.assertNotIn('fetch("archive/', verdict_updater)
        self.assertNotIn("loadFred('fred-data.json')", charts_macro)
        self.assertNotIn('loadFred("fred-data.json")', charts_macro)


if __name__ == "__main__":
    unittest.main()
