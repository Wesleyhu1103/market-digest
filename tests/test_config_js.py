import json
import subprocess
import unittest
from pathlib import Path

CONFIG_JS = Path(__file__).resolve().parents[1] / "docs" / "js" / "config.js"


class ConfigJsTests(unittest.TestCase):
    def md_site_path(self, pathname, rel):
        code = f"""
global.location = {{ pathname: {json.dumps(pathname)}, hostname: "wesleyhu1103.github.io" }};
eval(require("fs").readFileSync({json.dumps(str(CONFIG_JS))}, "utf8"));
process.stdout.write(mdSitePath({json.dumps(rel)}));
"""
        result = subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True)
        return result.stdout

    def test_md_site_path_resolves_from_archive_pages_to_site_root(self):
        self.assertEqual(
            self.md_site_path("/market-digest/archive/2026-08-31.html", "fred-data.json"),
            "/market-digest/fred-data.json",
        )
        self.assertEqual(
            self.md_site_path("/market-digest/archive/2026-08-31.html", "archive/manifest.json"),
            "/market-digest/archive/manifest.json",
        )

    def test_md_site_path_preserves_live_page_site_root(self):
        self.assertEqual(
            self.md_site_path("/market-digest/index.html", "archive/manifest.json"),
            "/market-digest/archive/manifest.json",
        )


if __name__ == "__main__":
    unittest.main()
