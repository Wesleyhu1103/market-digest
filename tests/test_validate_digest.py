import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_digest.py"


def load_validate_digest():
    import sys

    spec = importlib.util.spec_from_file_location("validate_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_digest"] = module
    spec.loader.exec_module(module)
    return module


class ValidateDigestTests(unittest.TestCase):
    def test_missing_local_assets_reports_paths_relative_to_html(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "docs" / "archive"
            archive.mkdir(parents=True)
            html_path = archive / "2026-07-09.html"
            html_path.write_text(
                '<script src="js/site-config.js?v=1"></script>\n'
                '<link rel="stylesheet" href="../css/digest.css?v=1">\n'
                '<script src="https://example.com/chart.js"></script>'
            )
            (root / "docs" / "css").mkdir()
            (root / "docs" / "css" / "digest.css").write_text("")

            missing = module.missing_local_assets(html_path.read_text(), html_path)

        self.assertEqual(missing, ["js/site-config.js?v=1"])


if __name__ == "__main__":
    unittest.main()
