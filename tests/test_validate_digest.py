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

    def test_validate_archive_runtime_paths_flags_page_relative_fetches(self):
        module = load_validate_digest()
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "docs" / "archive"
            archive.mkdir(parents=True)
            html_path = archive / "2026-07-21.html"
            html = """
            <script>
              function sitePath(rel) {
                var path = window.location.pathname || '/';
                return path + rel;
              }
              fetch('fred-data.json', { cache: 'no-store' });
              fetch('archive/manifest.json', { cache: 'no-store' });
              loadFred('fred-data.json');
              function macroFredUrl() { return 'fred-data.json'; }
            </script>
            """

            failures = module.validate_archive_runtime_paths(html, html_path)

            self.assertEqual(len(failures), 5)
            self.assertTrue(any("fred-data.json fetch" in item for item in failures))
            self.assertTrue(any("archive/... fetch" in item for item in failures))
            self.assertTrue(any("sitePath helper" in item for item in failures))

    def test_validate_archive_runtime_paths_accepts_site_root_fetches(self):
        module = load_validate_digest()
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "docs" / "archive"
            archive.mkdir(parents=True)
            html_path = archive / "2026-07-21.html"
            html = """
            <script>
              function sitePath(rel) {
                var clean = String(rel || '').replace(/^\\//, '');
                var path = window.location.pathname || '/';
                var archiveIdx = path.indexOf('/archive/');
                if (archiveIdx >= 0) return path.slice(0, archiveIdx + 1) + clean;
                return path + clean;
              }
              fetch('../fred-data.json', { cache: 'no-store' });
              fetch('../archive/manifest.json', { cache: 'no-store' });
              loadFred('../fred-data.json');
            </script>
            """

            failures = module.validate_archive_runtime_paths(html, html_path)

            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
