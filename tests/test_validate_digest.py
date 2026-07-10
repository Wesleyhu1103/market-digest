import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_digest.py"


def load_validate_digest():
    spec = importlib.util.spec_from_file_location("validate_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidateDigestTests(unittest.TestCase):
    def test_check_local_assets_fails_unresolved_archive_refs(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "archive"
            archive.mkdir()
            html_path = archive / "2026-07-09.html"
            html_path.write_text(
                '<script src="js/site-config.js?v=1"></script>'
                '<link rel="stylesheet" href="css/digest.css?v=1">'
            )

            self.assertFalse(module.check_local_assets(html_path.read_text(), html_path))

    def test_check_local_assets_accepts_archive_safe_refs(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "archive"
            js = root / "js"
            css = root / "css"
            archive.mkdir()
            js.mkdir()
            css.mkdir()
            (js / "site-config.js").write_text("var ok = true;")
            (css / "digest.css").write_text("body{}")
            html_path = archive / "2026-07-09.html"
            html_path.write_text(
                '<script src="../js/site-config.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1">'
            )

            self.assertTrue(module.check_local_assets(html_path.read_text(), html_path))


if __name__ == "__main__":
    unittest.main()
