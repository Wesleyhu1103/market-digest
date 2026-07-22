import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_digest.py"


def load_validate_digest():
    spec = importlib.util.spec_from_file_location("validate_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_digest"] = module
    spec.loader.exec_module(module)
    return module


class ValidateDigestTests(unittest.TestCase):
    def test_validate_local_assets_flags_missing_archive_js_and_css(self):
        module = load_validate_digest()
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "docs" / "archive"
            archive.mkdir(parents=True)
            html_path = archive / "2026-07-21.html"
            html_path.write_text(
                """
                <html><head>
                  <script src="js/app.js?v=1"></script>
                  <link rel="stylesheet" href="css/digest.css?v=1">
                  <script src="https://cdn.example/app.js"></script>
                </head><body></body></html>
                """
            )

            missing = module.validate_local_assets(html_path.read_text(), html_path)

            self.assertEqual(len(missing), 2)
            self.assertTrue(any("script js/app.js?v=1" in item for item in missing))
            self.assertTrue(any("stylesheet css/digest.css?v=1" in item for item in missing))

    def test_validate_local_assets_accepts_archive_safe_paths(self):
        module = load_validate_digest()
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            archive = docs / "archive"
            (docs / "js").mkdir(parents=True)
            (docs / "css").mkdir()
            archive.mkdir()
            (docs / "js" / "app.js").write_text("var ok = true;")
            (docs / "css" / "digest.css").write_text("body{}")
            html_path = archive / "2026-07-21.html"
            html_path.write_text(
                """
                <html><head>
                  <script src="../js/app.js?v=1"></script>
                  <link rel="stylesheet" href="../css/digest.css?v=1">
                </head><body></body></html>
                """
            )

            missing = module.validate_local_assets(html_path.read_text(), html_path)

            self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
