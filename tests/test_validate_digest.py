import contextlib
import importlib.util
import io
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
    def test_local_archive_assets_must_exist_at_resolved_paths(self):
        module = load_validate_digest()

        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            archive = docs / "archive"
            js = docs / "js"
            css = docs / "css"
            archive.mkdir(parents=True)
            js.mkdir()
            css.mkdir()
            (js / "app.js").write_text("window.ok = true;\n")
            (css / "digest.css").write_text("body { color: black; }\n")

            module.DOCS_ROOT = docs
            archive_page = archive / "2026-07-15.html"

            broken = '<script src="js/app.js"></script><link rel="stylesheet" href="css/digest.css">'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(module.validate_local_assets(broken, archive_page))

            fixed = '<script src="../js/app.js"></script><link rel="stylesheet" href="../css/digest.css">'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(module.validate_local_assets(fixed, archive_page))


if __name__ == "__main__":
    unittest.main()
