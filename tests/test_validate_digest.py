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
    def test_missing_local_assets_reports_archive_relative_script_and_stylesheet(self):
        module = load_validate_digest()
        html = """
        <script src="js/app.js?v=1"></script>
        <link rel="stylesheet" href="css/digest.css?v=1">
        <link rel="preconnect" href="css/not-a-stylesheet.css">
        """

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "docs" / "archive" / "2026-07-16.html"
            html_path.parent.mkdir(parents=True)
            html_path.write_text(html)

            missing = module.missing_local_assets(html, html_path)

        self.assertEqual(missing, ["js/app.js?v=1", "css/digest.css?v=1"])

    def test_collect_js_does_not_fetch_live_fallback_for_missing_local_script(self):
        module = load_validate_digest()
        html = '<script src="js/missing.js?v=1"></script><script>window.inline = true;</script>'

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "docs" / "archive" / "2026-07-16.html"
            html_path.parent.mkdir(parents=True)
            html_path.write_text(html)

            with mock.patch.object(module, "_fetch_text") as fetch_text:
                js_bundle = module.collect_js(html, html_path)

        fetch_text.assert_not_called()
        self.assertEqual(js_bundle.strip(), "window.inline = true;")


if __name__ == "__main__":
    unittest.main()
