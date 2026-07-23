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
    def test_validate_local_assets_checks_paths_from_html_file(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "js").mkdir()
            (root / "css").mkdir()
            (root / "archive").mkdir()
            (root / "js" / "digest-ui.js").write_text("console.log('ok');")
            (root / "css" / "digest.css").write_text("body{}")
            archive = root / "archive" / "2026-07-22.html"

            broken = '<script src="js/digest-ui.js?v=1"></script><link rel="stylesheet" href="css/digest.css?v=1">'
            fixed = '<script src="../js/digest-ui.js?v=1"></script><link rel="stylesheet" href="../css/digest.css?v=1">'

            self.assertEqual(
                module.validate_local_assets(broken, archive),
                ["js/digest-ui.js?v=1", "css/digest.css?v=1"],
            )
            self.assertEqual(module.validate_local_assets(fixed, archive), [])


if __name__ == "__main__":
    unittest.main()
