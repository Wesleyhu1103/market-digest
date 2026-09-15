import json
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimePathTests(unittest.TestCase):
    def run_node(self, script: str) -> None:
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_site_paths_resolve_from_archive_pages(self):
        site_config = (ROOT / "docs" / "js" / "site-config.js").read_text()
        config = (ROOT / "docs" / "js" / "config.js").read_text()
        script = textwrap.dedent(
            f"""
            const assert = require('assert');
            const vm = require('vm');
            const siteConfig = {json.dumps(site_config)};
            const config = {json.dumps(config)};

            function run(hostname, pathname) {{
              const context = {{ location: {{ hostname, pathname }}, console }};
              context.window = context;
              vm.runInNewContext(siteConfig + '\\n' + config + `\\nresult = {{
                archiveManifest: mdSitePath('archive/manifest.json'),
                archiveHtml: mdSitePath('archive/2026-09-14.html'),
                fred: mdMacroFredUrl()
              }};`, context);
              return context.result;
            }}

            assert.deepStrictEqual(
              JSON.parse(JSON.stringify(
              run('wesleyhu1103.github.io', '/market-digest/archive/2026-09-14.html'),
              )),
              {{
                archiveManifest: '/market-digest/archive/manifest.json',
                archiveHtml: '/market-digest/archive/2026-09-14.html',
                fred: '/market-digest/fred-data.json'
              }}
            );
            assert.deepStrictEqual(
              JSON.parse(JSON.stringify(
              run('market-digest-liart.vercel.app', '/archive/2026-09-14.html'),
              )),
              {{
                archiveManifest: '/archive/manifest.json',
                archiveHtml: '/archive/2026-09-14.html',
                fred: '/api/fred-data'
              }}
            );
            assert.strictEqual(
              run('wesleyhu1103.github.io', '/market-digest/').archiveManifest,
              '/market-digest/archive/manifest.json'
            );
            """
        )
        self.run_node(script)

    def test_archive_runtime_fetches_do_not_use_archive_relative_roots(self):
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_macro_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("window.mdSitePath(rel)", archive_js)
        self.assertIn("sitePath('archive/manifest.json')", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_macro_js)
        self.assertNotIn("loadFred('fred-data.json')", charts_macro_js)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict_js)


if __name__ == "__main__":
    unittest.main()
