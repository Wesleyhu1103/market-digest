import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SitePathTests(unittest.TestCase):
    def test_site_paths_resolve_from_archive_pages(self):
        config_js = (ROOT / "docs" / "js" / "config.js").read_text()
        script = (
            "global.window = global;\n"
            "global.MD_VERCEL_ORIGIN = 'https://market-digest-liart.vercel.app';\n"
            "global.location = { hostname: 'wesleyhu1103.github.io', pathname: '/market-digest/archive/2026-08-17.html' };\n"
            + config_js
            + textwrap.dedent(
                """
                function assertEq(actual, expected) {
                  if (actual !== expected) throw new Error(actual + ' !== ' + expected);
                }
                assertEq(mdSitePath('archive/manifest.json'), '/market-digest/archive/manifest.json');
                assertEq(mdMacroFredUrl(), '/market-digest/fred-data.json');
                location = { hostname: 'market-digest-liart.vercel.app', pathname: '/archive/2026-08-17.html' };
                assertEq(mdSitePath('archive/2026-08-14.html'), '/archive/2026-08-14.html');
                assertEq(mdSitePath('fred-data.json'), '/fred-data.json');
                location = { hostname: 'localhost', pathname: '/index.html' };
                assertEq(mdSitePath('archive/manifest.json'), '/archive/manifest.json');
                """
            )
        )

        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_fetches_use_site_root_helper(self):
        checks = {
            "docs/js/archive.js": ["mdSitePath(rel)", "window.location.pathname"],
            "docs/js/charts-macro.js": ["mdSitePath('fred-data.json')", "loadFred('fred-data.json')"],
            "docs/js/verdict-updater.js": ["mdSitePath('archive/' + iso + '.html')", "fetch('archive/'"],
        }
        for rel, (required, forbidden) in checks.items():
            body = (ROOT / rel).read_text()
            with self.subTest(file=rel):
                self.assertIn(required, body)
                self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()
