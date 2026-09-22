import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticRuntimePathTests(unittest.TestCase):
    def test_shared_js_uses_root_aware_site_paths(self):
        config_js = (ROOT / "docs" / "js" / "config.js").read_text()
        archive_js = (ROOT / "docs" / "js" / "archive.js").read_text()
        charts_js = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict_js = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("function mdSitePath(", config_js)
        self.assertIn("return mdSitePath(rel)", archive_js)
        self.assertIn("mdSitePath('fred-data.json')", charts_js)
        self.assertIn("mdSitePath('archive/' + iso + '.html')", verdict_js)

    def test_no_bare_archive_relative_data_fetches_remain(self):
        pattern = re.compile(
            r"(?:fetch|loadFred)\(['\"](?:archive/|fred-data\.json)|return ['\"]fred-data\.json['\"]"
        )
        paths = list((ROOT / "docs" / "js").glob("*.js")) + list((ROOT / "docs" / "archive").glob("*.html"))
        offenders = []
        for path in paths:
            for line_no, line in enumerate(path.read_text().splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{line_no}:{line.strip()}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
