import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_config_expression(hostname: str, pathname: str, expression: str) -> str:
    code = f"""
global.location = {json.dumps({"hostname": hostname, "pathname": pathname})};
global.window = global;
const fs = require('fs');
const vm = require('vm');
vm.runInThisContext(fs.readFileSync({json.dumps(str(ROOT / "docs" / "js" / "config.js"))}, 'utf8'));
console.log({expression});
"""
    result = subprocess.run(
        ["node", "-e", code],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_site_path_resolves_github_pages_archives_to_repo_root(self):
        self.assertEqual(
            run_config_expression(
                "wesleyhu1103.github.io",
                "/market-digest/archive/2026-08-20.html",
                "mdSitePath('archive/manifest.json')",
            ),
            "/market-digest/archive/manifest.json",
        )
        self.assertEqual(
            run_config_expression(
                "wesleyhu1103.github.io",
                "/market-digest/archive/2026-08-20.html",
                "mdMacroFredUrl()",
            ),
            "/market-digest/fred-data.json",
        )

    def test_site_path_resolves_local_archives_to_site_root(self):
        self.assertEqual(
            run_config_expression(
                "localhost",
                "/archive/2026-08-20.html",
                "mdSitePath('fred-data.json')",
            ),
            "/fred-data.json",
        )

    def test_archive_runtime_callers_use_root_helper(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("mdSitePath(rel)", archive_js)
        self.assertIn("archivePath('archive/manifest.json')", archive_js)
        self.assertIn("archivePath(e.url || '')", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict_js)


if __name__ == "__main__":
    unittest.main()
