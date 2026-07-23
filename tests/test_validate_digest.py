import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_digest import validate_local_assets  # noqa: E402


class ValidateDigestTest(unittest.TestCase):
    def test_validate_local_assets_reports_archive_relative_misses(self):
        html = (
            '<script src="js/site-config.js?v=1"></script>\n'
            '<link rel="stylesheet" href="css/digest.css?v=1">\n'
            '<script src="https://cdn.example/app.js"></script>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "archive" / "2026-07-22.html"
            html_path.parent.mkdir()
            html_path.write_text(html)

            missing = validate_local_assets(html, html_path)

        self.assertEqual(missing, ["js/site-config.js", "css/digest.css"])


if __name__ == "__main__":
    unittest.main()
