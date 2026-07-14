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
    def test_missing_local_archive_assets_are_reported(self):
        module = load_validate_digest()
        html = """<head>
<script src="js/site-config.js?v=1"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
</head>"""

        with tempfile.TemporaryDirectory() as tmp:
            archive_html = Path(tmp) / "docs" / "archive" / "2026-07-13.html"
            archive_html.parent.mkdir(parents=True)
            archive_html.write_text(html)

            missing = module.missing_local_assets(html, archive_html)

        self.assertEqual(missing, ["js/site-config.js?v=1", "css/digest.css?v=1"])

    def test_archive_safe_relative_assets_are_found(self):
        module = load_validate_digest()
        html = """<head>
<script src="../js/site-config.js?v=1"></script>
<link rel="stylesheet" href="../css/digest.css?v=1">
</head>"""

        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            (docs / "archive").mkdir(parents=True)
            (docs / "js").mkdir()
            (docs / "css").mkdir()
            (docs / "js" / "site-config.js").write_text("window.SiteConfig={};")
            (docs / "css" / "digest.css").write_text("body{}")
            archive_html = docs / "archive" / "2026-07-13.html"
            archive_html.write_text(html)

            missing = module.missing_local_assets(html, archive_html)

        self.assertEqual(missing, [])

    def test_collect_js_does_not_fall_back_to_remote_for_local_missing_script(self):
        module = load_validate_digest()
        html = '<script src="js/site-config.js?v=1"></script>'

        def fail_fetch(url):
            raise AssertionError(f"unexpected remote fetch for {url}")

        with tempfile.TemporaryDirectory() as tmp:
            archive_html = Path(tmp) / "docs" / "archive" / "2026-07-13.html"
            archive_html.parent.mkdir(parents=True)
            archive_html.write_text(html)
            module._fetch_text = fail_fetch

            js = module.collect_js(html, archive_html)

        self.assertEqual(js, "")


if __name__ == "__main__":
    unittest.main()
