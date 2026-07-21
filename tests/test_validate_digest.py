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
    def test_local_archive_asset_misses_are_errors(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "archive" / "day.html"
            page.parent.mkdir()
            page.write_text(
                """<!doctype html>
<script src="js/app.js"></script>
<link rel="stylesheet" href="css/app.css">
<main></main>"""
            )

            js, script_errors = module.collect_js(page.read_text(), page)
            style_errors = module.check_local_stylesheets(page.read_text(), page)

        self.assertEqual(js, "")
        self.assertEqual(script_errors, ["missing local script asset: js/app.js"])
        self.assertEqual(style_errors, ["missing local stylesheet asset: css/app.css"])

    def test_archive_relative_asset_paths_resolve(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "js").mkdir()
            (root / "css").mkdir()
            (root / "archive").mkdir()
            (root / "js" / "app.js").write_text("const ok = true;")
            (root / "css" / "app.css").write_text("body { color: black; }")
            page = root / "archive" / "day.html"
            page.write_text(
                """<!doctype html>
<script src="../js/app.js?v=1"></script>
<link rel="stylesheet" href="../css/app.css?v=1">
<main></main>"""
            )

            js, script_errors = module.collect_js(page.read_text(), page)
            style_errors = module.check_local_stylesheets(page.read_text(), page)

        self.assertIn("const ok = true;", js)
        self.assertEqual(script_errors, [])
        self.assertEqual(style_errors, [])


if __name__ == "__main__":
    unittest.main()
