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
    def test_missing_local_assets_resolves_relative_to_html_file(self):
        module = load_validate_digest()
        html = """
        <script src="js/app.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        """

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "docs" / "archive" / "page.html"
            page.parent.mkdir(parents=True)

            self.assertEqual(
                module.missing_local_assets(html, page),
                ["js/app.js?v=1", "css/digest.css?v=1"],
            )

    def test_archive_safe_local_assets_are_not_reported_missing(self):
        module = load_validate_digest()
        html = """
        <script src="../js/app.js?v=1"></script>
        <link rel="stylesheet" href="../css/digest.css?v=1">
        """

        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            page = docs / "archive" / "page.html"
            (docs / "archive").mkdir(parents=True)
            (docs / "js").mkdir()
            (docs / "css").mkdir()
            (docs / "js" / "app.js").write_text("window.ok = true;")
            (docs / "css" / "digest.css").write_text("body {}")

            self.assertEqual(module.missing_local_assets(html, page), [])

    def test_collect_js_does_not_fetch_live_fallback_for_missing_local_file(self):
        module = load_validate_digest()
        html = '<script src="js/missing.js?v=1"></script><script>window.inline = true;</script>'

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "docs" / "archive" / "page.html"
            page.parent.mkdir(parents=True)
            with mock.patch.object(module, "_fetch_text", side_effect=AssertionError):
                self.assertEqual(module.collect_js(html, page).strip(), "window.inline = true;")


if __name__ == "__main__":
    unittest.main()
