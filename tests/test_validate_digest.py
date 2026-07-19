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
    def test_archive_relative_local_assets_must_exist(self):
        module = load_validate_digest()
        html = """<!doctype html>
<script src="js/missing.js?v=1"></script>
<link rel="stylesheet" href="css/missing.css?v=1">
<script src="https://cdn.example/chart.js"></script>"""

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "archive" / "2026-07-17.html"
            page.parent.mkdir()
            page.write_text(html)

            errors = module.local_asset_errors(html, page)

        self.assertEqual(len(errors), 2)
        self.assertIn("missing local script asset", errors[0])
        self.assertIn("missing local stylesheet asset", errors[1])

    def test_archive_safe_relative_assets_pass_existence_check(self):
        module = load_validate_digest()
        html = """<!doctype html>
<script src="../js/app.js?v=1"></script>
<link rel="stylesheet" href="../css/site.css?v=1">"""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "archive").mkdir()
            (root / "js").mkdir()
            (root / "css").mkdir()
            (root / "js" / "app.js").write_text("window.ok = true;")
            (root / "css" / "site.css").write_text("body{}")
            page = root / "archive" / "2026-07-17.html"
            page.write_text(html)

            errors = module.local_asset_errors(html, page)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
