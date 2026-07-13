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
    def test_local_asset_failures_catches_archive_relative_misses(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "archive"
            archive.mkdir()
            (root / "js").mkdir()
            (root / "css").mkdir()
            (root / "js" / "app.js").write_text("")
            (root / "css" / "digest.css").write_text("")
            html_path = archive / "2026-07-10.html"
            html_path.write_text("")

            broken = '<script src="js/app.js?v=1"></script><link href="css/digest.css?v=1" rel="stylesheet">'
            fixed = '<script src="../js/app.js?v=1"></script><link href="../css/digest.css?v=1" rel="stylesheet">'

            self.assertEqual(
                module.local_asset_failures(broken, html_path),
                ["js/app.js?v=1", "css/digest.css?v=1"],
            )
            self.assertEqual(module.local_asset_failures(fixed, html_path), [])


if __name__ == "__main__":
    unittest.main()
