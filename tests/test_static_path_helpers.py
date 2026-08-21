import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticPathHelperTests(unittest.TestCase):
    def run_config_case(self, hostname, pathname, edition_iso="2026-08-10", today_iso="2026-08-11"):
        script = textwrap.dedent(
            """
            const fs = require('fs');
            const config = fs.readFileSync('docs/js/config.js', 'utf8');
            const hostname = process.argv[1];
            const pathname = process.argv[2];
            const editionIso = process.argv[3];
            const todayIso = process.argv[4];
            const location = { hostname, pathname };
            const RealDate = Date;
            class FakeDate extends RealDate {
              constructor(...args) {
                if (args.length) super(...args);
                else super(todayIso + 'T16:00:00Z');
              }
              static now() { return new RealDate(todayIso + 'T16:00:00Z').getTime(); }
            }
            FakeDate.UTC = RealDate.UTC;
            FakeDate.parse = RealDate.parse;
            const DigestDate = {
              headerEdition() { return editionIso ? { iso: editionIso } : null; }
            };
            const window = { location, DigestDate };
            const localStorage = { getItem() { return null; }, setItem() {} };
            const crypto = { randomUUID() { return 'test-id'; } };
            const helpers = new Function(
              'window', 'location', 'localStorage', 'crypto', 'MD_VERCEL_ORIGIN', 'Date', 'DigestDate',
              config + '\\nreturn { mdSitePath, mdMacroFredUrl, mdScoreboardAnchorIso, mdScoreboardRowIso };'
            )(window, location, localStorage, crypto, 'https://api.example', FakeDate, DigestDate);
            console.log(JSON.stringify({
              fred: helpers.mdSitePath('fred-data.json'),
              archived: helpers.mdSitePath('archive/2026-08-10.html'),
              macro: helpers.mdMacroFredUrl(),
              anchor: helpers.mdScoreboardAnchorIso(),
              rowDec: helpers.mdScoreboardRowIso('Mon 12/29'),
              rowJan: helpers.mdScoreboardRowIso('Fri 1/2')
            }));
            """
        )
        proc = subprocess.run(
            ["node", "-e", script, hostname, pathname, edition_iso, today_iso],
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

    def test_scoreboard_anchor_caps_archives_at_edition_date(self):
        result = self.run_config_case(
            "wesleyhu1103.github.io",
            "/market-digest/archive/2026-08-10.html",
            edition_iso="2026-08-10",
            today_iso="2026-08-12",
        )

        self.assertEqual(result["anchor"], "2026-08-10")

    def test_scoreboard_row_iso_handles_january_week_with_december_rows(self):
        result = self.run_config_case(
            "wesleyhu1103.github.io",
            "/market-digest/",
            edition_iso="2027-01-02",
            today_iso="2027-01-02",
        )

        self.assertEqual(result["rowDec"], "2026-12-29")
        self.assertEqual(result["rowJan"], "2027-01-02")

    def test_scoreboard_row_iso_handles_december_week_with_january_rows(self):
        result = self.run_config_case(
            "wesleyhu1103.github.io",
            "/market-digest/",
            edition_iso="2026-12-30",
            today_iso="2026-12-30",
        )

        self.assertEqual(result["rowDec"], "2026-12-29")
        self.assertEqual(result["rowJan"], "2027-01-02")


if __name__ == "__main__":
    unittest.main()
