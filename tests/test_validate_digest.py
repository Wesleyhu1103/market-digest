import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_digest  # noqa: E402


class ValidateDigestLocalAssetsTest(unittest.TestCase):
    def test_local_asset_failures_rejects_missing_archive_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "archive" / "2026-07-16.html"
            html_path.parent.mkdir()
            html = """<!doctype html>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
"""

            self.assertEqual(validate_digest.local_asset_failures(html, html_path), 2)

    def test_collect_js_does_not_fallback_when_local_script_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "archive" / "2026-07-16.html"
            html_path.parent.mkdir()
            html = '<script src="js/site-config.js?v=1"></script>'

            self.assertEqual(validate_digest.collect_js(html, html_path), "")


if __name__ == "__main__":
    unittest.main()
