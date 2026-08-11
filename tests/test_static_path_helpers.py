import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticPathHelperTests(unittest.TestCase):
    def run_config_case(self, hostname, pathname):
        script = textwrap.dedent(
            """
            const fs = require('fs');
            const config = fs.readFileSync('docs/js/config.js', 'utf8');
            const hostname = process.argv[1];
            const pathname = process.argv[2];
            const location = { hostname, pathname };
            const window = { location };
            const localStorage = { getItem() { return null; }, setItem() {} };
            const crypto = { randomUUID() { return 'test-id'; } };
            const helpers = new Function(
              'window', 'location', 'localStorage', 'crypto', 'MD_VERCEL_ORIGIN',
              config + '\\nreturn { mdSitePath, mdMacroFredUrl };'
            )(window, location, localStorage, crypto, 'https://api.example');
            console.log(JSON.stringify({
              fred: helpers.mdSitePath('fred-data.json'),
              archived: helpers.mdSitePath('archive/2026-08-10.html'),
              macro: helpers.mdMacroFredUrl()
            }));
            """
        )
        proc = subprocess.run(
            ["node", "-e", script, hostname, pathname],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(proc.stdout)

    def test_github_pages_archive_resolves_static_files_from_site_root(self):
        result = self.run_config_case(
            "wesleyhu1103.github.io",
            "/market-digest/archive/2026-08-10.html",
        )

        self.assertEqual(result["fred"], "/market-digest/fred-data.json")
        self.assertEqual(result["archived"], "/market-digest/archive/2026-08-10.html")
        self.assertEqual(result["macro"], "/market-digest/fred-data.json")

    def test_github_pages_live_page_keeps_project_root_prefix(self):
        result = self.run_config_case("wesleyhu1103.github.io", "/market-digest/")

        self.assertEqual(result["fred"], "/market-digest/fred-data.json")
        self.assertEqual(result["macro"], "/market-digest/fred-data.json")

    def test_local_archive_resolves_static_files_from_docs_root(self):
        result = self.run_config_case("localhost", "/archive/2026-08-10.html")

        self.assertEqual(result["fred"], "/fred-data.json")
        self.assertEqual(result["archived"], "/archive/2026-08-10.html")
        self.assertEqual(result["macro"], "/api/fred-data")

    def test_scoreboard_archive_fetch_uses_site_path_helper(self):
        js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("mdSitePath('archive/' + iso + '.html')", js)


if __name__ == "__main__":
    unittest.main()
