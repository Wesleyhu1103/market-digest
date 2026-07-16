import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_digest import collect_js, collect_local_asset_errors  # noqa: E402


class ValidateDigestTest(unittest.TestCase):
    def test_archive_relative_assets_must_exist_at_referenced_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "docs"
            archive = root / "archive"
            (root / "js").mkdir(parents=True)
            (root / "css").mkdir()
            archive.mkdir()
            (root / "js" / "digest-ui.js").write_text("window.ok = true;")
            (root / "css" / "digest.css").write_text("body{}")
            html_path = archive / "2026-07-15.html"
            html_path.write_text(
                '<script src="js/digest-ui.js?v=1"></script>'
                '<link rel="stylesheet" href="css/digest.css?v=1">'
            )

            errors = collect_local_asset_errors(html_path.read_text(), html_path)

        self.assertEqual(len(errors), 2)
        self.assertIn("js/digest-ui.js?v=1", errors[0])
        self.assertIn("css/digest.css?v=1", errors[1])

    def test_archive_safe_relative_assets_are_loaded_from_parent_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "docs"
            archive = root / "archive"
            (root / "js").mkdir(parents=True)
            (root / "css").mkdir()
            archive.mkdir()
            (root / "js" / "digest-ui.js").write_text("window.ok = true;")
            (root / "css" / "digest.css").write_text("body{}")
            html_path = archive / "2026-07-15.html"
            html = (
                '<script src="../js/digest-ui.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )
            html_path.write_text(html)

            self.assertEqual(collect_local_asset_errors(html, html_path), [])
            self.assertIn("window.ok = true;", collect_js(html, html_path))


if __name__ == "__main__":
    unittest.main()
