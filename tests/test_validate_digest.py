import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_digest  # noqa: E402


class ValidateDigestAssetTest(unittest.TestCase):
    def test_missing_local_assets_reports_archive_relative_breakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "docs" / "archive" / "2026-07-21.html"
            page.parent.mkdir(parents=True)
            html = (
                '<script src="js/app.js?v=1"></script>\n'
                '<link rel="stylesheet" href="css/digest.css?v=1">'
            )

            missing = validate_digest.missing_local_assets(html, page)

            self.assertIn("script js/app.js?v=1", missing)
            self.assertIn("stylesheet css/digest.css?v=1", missing)

    def test_missing_local_assets_accepts_archive_safe_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "docs"
            page = root / "archive" / "2026-07-21.html"
            (root / "archive").mkdir(parents=True)
            (root / "js").mkdir()
            (root / "css").mkdir()
            (root / "js" / "app.js").write_text("window.ok = true;")
            (root / "css" / "digest.css").write_text("body{}")
            html = (
                '<script src="../js/app.js?v=1"></script>\n'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            missing = validate_digest.missing_local_assets(html, page)

            self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
