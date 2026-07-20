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
    def test_check_local_assets_rejects_archive_relative_missing_assets(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "docs" / "archive" / "2026-07-17.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                """
                <script src="js/site-config.js?v=1"></script>
                <link rel="stylesheet" href="css/digest.css?v=1">
                <main></main>
                """
            )

            self.assertFalse(module.check_local_assets(page.read_text(), page))

    def test_check_local_assets_accepts_archive_safe_paths(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            (docs / "archive").mkdir(parents=True)
            (docs / "js").mkdir()
            (docs / "css").mkdir()
            (docs / "js" / "site-config.js").write_text("window.SiteConfig = {};")
            (docs / "css" / "digest.css").write_text("body{}")
            page = docs / "archive" / "2026-07-17.html"
            page.write_text(
                """
                <script src="../js/site-config.js?v=1"></script>
                <link rel="stylesheet" href="../css/digest.css?v=1">
                <main></main>
                """
            )

            self.assertTrue(module.check_local_assets(page.read_text(), page))


if __name__ == "__main__":
    unittest.main()
