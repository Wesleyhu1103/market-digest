import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_digest.py"


def load_validate_digest():
    spec = importlib.util.spec_from_file_location("validate_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidateDigestTests(unittest.TestCase):
    def test_archive_local_assets_must_resolve_relative_to_archive(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "archive").mkdir(parents=True)
            (root / "docs" / "js").mkdir()
            (root / "docs" / "css").mkdir()
            (root / "docs" / "js" / "app.js").write_text("window.ok = true;")
            (root / "docs" / "css" / "digest.css").write_text("body{}")
            archive_path = root / "docs" / "archive" / "day.html"

            bad_html = '<script src="js/app.js"></script><link rel="stylesheet" href="css/digest.css">'
            good_html = '<script src="../js/app.js"></script><link rel="stylesheet" href="../css/digest.css">'

            self.assertEqual(
                module.local_asset_failures(good_html, archive_path),
                [],
            )
            self.assertEqual(
                module.local_asset_failures(bad_html, archive_path),
                ["missing local script js/app.js", "missing local stylesheet css/digest.css"],
            )

    def test_collect_js_does_not_fallback_for_missing_local_script(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "docs" / "archive" / "day.html"
            html_path.parent.mkdir(parents=True)

            with mock.patch.object(module, "_fetch_text", side_effect=AssertionError("fallback used")):
                self.assertEqual(module.collect_js('<script src="js/missing.js"></script>', html_path), "")


if __name__ == "__main__":
    unittest.main()
