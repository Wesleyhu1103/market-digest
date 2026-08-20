import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"


class ArchiveRuntimePathTests(unittest.TestCase):
    def run_config_helper(self, pathname, rel, hostname="wesleyhu1103.github.io"):
        script = textwrap.dedent(
            f"""
            global.MD_VERCEL_ORIGIN = "https://market-digest-liart.vercel.app";
            global.window = {{ location: {{ pathname: {json.dumps(pathname)}, hostname: {json.dumps(hostname)} }} }};
            global.location = global.window.location;
            {CONFIG_JS.read_text()}
            console.log(JSON.stringify({{
              sitePath: mdSitePath({json.dumps(rel)}),
              fredPath: mdMacroFredUrl()
            }}));
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_archive_page_paths_resolve_from_site_root(self):
        out = self.run_config_helper(
            "/market-digest/archive/2026-08-19.html",
            "archive/manifest.json",
        )

        self.assertEqual(out["sitePath"], "/market-digest/archive/manifest.json")
        self.assertEqual(out["fredPath"], "/market-digest/fred-data.json")

    def test_live_page_paths_stay_root_relative_to_current_site(self):
        out = self.run_config_helper("/market-digest/index.html", "archive/manifest.json")

        self.assertEqual(out["sitePath"], "/market-digest/archive/manifest.json")
        self.assertEqual(out["fredPath"], "/market-digest/fred-data.json")

    def test_runtime_modules_do_not_use_bare_archive_relative_fetches(self):
        verdict = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()
        archive = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts = (ROOT / "docs" / "js" / "charts-macro.js").read_text()

        self.assertNotIn("fetch('archive/'", verdict)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertIn("typeof mdSitePath === 'function'", archive)
        self.assertIn("mdSitePath('fred-data.json')", charts)


if __name__ == "__main__":
    unittest.main()
