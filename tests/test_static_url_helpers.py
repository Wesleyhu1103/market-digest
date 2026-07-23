import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_JS = ROOT / "docs" / "js" / "config.js"
ARCHIVE_JS = ROOT / "docs" / "js" / "archive.js"


def run_config_helpers(hostname, pathname):
    code = f"""
const vm = require('vm');
const context = {{
  location: {{ hostname: {json.dumps(hostname)}, pathname: {json.dumps(pathname)} }},
  console
}};
context.window = context;
vm.createContext(context);
vm.runInContext({json.dumps(CONFIG_JS.read_text())}, context);
console.log(JSON.stringify({{
  manifest: context.mdSiteRootPath('archive/manifest.json'),
  fred: context.mdMacroFredUrl()
}}));
"""
    result = subprocess.run(
        ["node", "-e", code],
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(result.stdout)


class StaticUrlHelperTests(unittest.TestCase):
    def test_github_archive_paths_resolve_from_repo_root(self):
        out = run_config_helpers(
            "wesleyhu1103.github.io",
            "/market-digest/archive/2026-07-22.html",
        )

        self.assertEqual(out["manifest"], "/market-digest/archive/manifest.json")
        self.assertEqual(out["fred"], "/market-digest/fred-data.json")

    def test_local_archive_paths_resolve_from_static_root(self):
        out = run_config_helpers("localhost", "/archive/2026-07-22.html")

        self.assertEqual(out["manifest"], "/archive/manifest.json")
        self.assertEqual(out["fred"], "/fred-data.json")

    def test_archive_script_uses_shared_site_root_helper(self):
        self.assertIn("mdSiteRootPath", ARCHIVE_JS.read_text())


if __name__ == "__main__":
    unittest.main()
