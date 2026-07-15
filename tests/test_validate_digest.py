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
    def test_check_local_assets_rejects_archive_relative_root_assets(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "docs" / "archive"
            archive.mkdir(parents=True)
            html_path = archive / "2026-07-14.html"
            html_path.write_text(
                '<html><head><script src="js/digest-ui.js?v=1"></script>'
                '<link rel="stylesheet" href="css/digest.css?v=1"></head></html>'
            )

            self.assertFalse(module.check_local_assets(html_path.read_text(), html_path))

    def test_check_local_assets_accepts_archive_safe_assets(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            archive = docs / "archive"
            (docs / "js").mkdir(parents=True)
            (docs / "css").mkdir()
            archive.mkdir()
            (docs / "js" / "digest-ui.js").write_text("")
            (docs / "css" / "digest.css").write_text("")
            html_path = archive / "2026-07-14.html"
            html_path.write_text(
                '<html><head><script src="../js/digest-ui.js?v=1"></script>'
                '<link rel="stylesheet" href="../css/digest.css?v=1"></head></html>'
            )

            self.assertTrue(module.check_local_assets(html_path.read_text(), html_path))


if __name__ == "__main__":
    unittest.main()
