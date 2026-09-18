import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticRuntimePathTests(unittest.TestCase):
    def test_md_site_path_resolves_from_archive_to_site_root(self):
        config_js = (ROOT / "docs" / "js" / "config.js").read_text()
        script = f"""
        const assert = require('assert');
        global.window = {{ location: {{ hostname: 'wesleyhu1103.github.io', pathname: '/market-digest/archive/2026-09-17.html' }} }};
        global.location = global.window.location;
        {config_js}
        assert.strictEqual(mdSiteBasePath(), '/market-digest/');
        assert.strictEqual(mdSitePath('archive/manifest.json'), '/market-digest/archive/manifest.json');
        assert.strictEqual(mdSitePath('/fred-data.json'), '/market-digest/fred-data.json');
        assert.strictEqual(mdMacroFredUrl(), '/market-digest/fred-data.json');
        location.pathname = '/market-digest/index.html';
        assert.strictEqual(mdSitePath('archive/manifest.json'), '/market-digest/archive/manifest.json');
        """

        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shared_js_does_not_fetch_archive_relative_data_from_archives(self):
        js_dir = ROOT / "docs" / "js"
        archive_js = (js_dir / "archive.js").read_text()
        charts_macro_js = (js_dir / "charts-macro.js").read_text()
        verdict_js = (js_dir / "verdict-updater.js").read_text()

        self.assertNotIn("function sitePath(", archive_js)
        self.assertIn("archivePath('archive/manifest.json')", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_macro_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)
        self.assertNotRegex(archive_js + verdict_js, r"fetch\(['\"]archive/")
        self.assertNotRegex(charts_macro_js, r"loadFred\(['\"]fred-data\.json['\"]")

    def test_archive_snapshots_do_not_use_archive_relative_runtime_paths(self):
        bad_patterns = [
            r"fetch\(['\"]archive/",
            r"loadFred\(['\"]fred-data\.json['\"]",
            r"return ['\"]fred-data\.json['\"]",
        ]
        for path in (ROOT / "docs" / "archive").glob("*.html"):
            text = path.read_text()
            for pattern in bad_patterns:
                self.assertNotRegex(text, pattern, str(path))
            if "function sitePath(rel)" in text:
                self.assertIn("path.indexOf('/archive/')", text, str(path))


if __name__ == "__main__":
    unittest.main()
