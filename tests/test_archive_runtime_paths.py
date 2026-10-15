import json
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_site_paths_resolve_from_archive_pages_to_site_root(self):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const code = fs.readFileSync({json.dumps(str(ROOT / 'docs/js/config.js'))}, 'utf8');

            function run(pathname, hostname, rel) {{
              const context = {{ location: {{ pathname, hostname }} }};
              vm.createContext(context);
              vm.runInContext(code, context);
              return {{
                sitePath: context.mdSitePath(rel),
                fredUrl: context.mdMacroFredUrl()
              }};
            }}

            console.log(JSON.stringify({{
              archiveProject: run('/market-digest/archive/2026-10-07.html', 'wesley.github.io', 'archive/manifest.json'),
              liveProject: run('/market-digest/index.html', 'wesley.github.io', 'archive/manifest.json'),
              archiveRoot: run('/archive/2026-10-07.html', 'market-digest-liart.vercel.app', 'fred-data.json'),
              localhost: run('/archive/2026-10-07.html', 'localhost', 'archive/manifest.json')
            }}));
            """
        )
        proc = subprocess.run(
            ["node", "-e", script],
            check=True,
            text=True,
            capture_output=True,
        )
        results = json.loads(proc.stdout)

        self.assertEqual(results["archiveProject"]["sitePath"], "/market-digest/archive/manifest.json")
        self.assertEqual(results["archiveProject"]["fredUrl"], "/market-digest/fred-data.json")
        self.assertEqual(results["liveProject"]["sitePath"], "/market-digest/archive/manifest.json")
        self.assertEqual(results["archiveRoot"]["sitePath"], "/fred-data.json")
        self.assertEqual(results["localhost"]["fredUrl"], "/api/fred-data")

    def test_shared_archive_fetches_use_root_aware_helper(self):
        charts_macro = (ROOT / "docs/js/charts-macro.js").read_text()
        verdict_updater = (ROOT / "docs/js/verdict-updater.js").read_text()

        self.assertNotIn("loadFred('fred-data.json')", charts_macro)
        self.assertNotIn('loadFred("fred-data.json")', charts_macro)
        self.assertNotIn("fetch('archive/'", verdict_updater)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_updater)


if __name__ == "__main__":
    unittest.main()
