import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_digest  # noqa: E402


class ValidateDigestAssetTests(unittest.TestCase):
    def test_archive_relative_assets_must_resolve_from_html_location(self):
        html = """<!doctype html>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "js").mkdir()
            (root / "css").mkdir()
            (root / "archive").mkdir()
            (root / "js" / "site-config.js").write_text("window.SiteConfig = {};")
            (root / "css" / "digest.css").write_text("body {}")
            archive_page = root / "archive" / "2026-07-13.html"
            archive_page.write_text(html)

            failures = validate_digest.local_asset_failures(html, archive_page)

        self.assertEqual([url for url, _ in failures], ["js/site-config.js?v=1", "css/digest.css?v=1"])

    def test_archive_safe_assets_resolve(self):
        html = """<!doctype html>
<script src="../js/site-config.js?v=1"></script>
<link rel="stylesheet" href="../css/digest.css?v=1">
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "js").mkdir()
            (root / "css").mkdir()
            (root / "archive").mkdir()
            (root / "js" / "site-config.js").write_text("window.SiteConfig = {};")
            (root / "css" / "digest.css").write_text("body {}")
            archive_page = root / "archive" / "2026-07-13.html"
            archive_page.write_text(html)

            failures = validate_digest.local_asset_failures(html, archive_page)

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
