import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_shared_runtime_paths_are_archive_safe(self):
        config = (ROOT / "docs" / "js" / "config.js").read_text()
        archive = (ROOT / "docs" / "js" / "archive.js").read_text()
        macro = (ROOT / "docs" / "js" / "charts-macro.js").read_text()
        verdict = (ROOT / "docs" / "js" / "verdict-updater.js").read_text()

        self.assertIn("function mdSiteBasePath()", config)
        self.assertIn("path.indexOf('/archive/')", config)
        self.assertIn("return mdSitePath('fred-data.json')", config)

        self.assertIn("mdSitePath(rel)", archive)
        self.assertIn("archivePath('archive/manifest.json')", archive)
        self.assertNotIn("fetch(sitePath('archive/manifest.json')", archive)

        self.assertIn("mdSitePath('fred-data.json')", macro)
        self.assertNotIn("loadFred('fred-data.json')", macro)

        self.assertIn("fetch(mdSitePath('archive/' + iso + '.html')", verdict)
        self.assertNotIn("fetch('archive/' + iso + '.html'", verdict)


if __name__ == "__main__":
    unittest.main()
