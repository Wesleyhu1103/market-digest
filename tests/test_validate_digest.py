import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_digest  # noqa: E402


class ValidateDigestLocalAssetsTest(unittest.TestCase):
    def test_local_asset_failures_resolve_relative_to_html_path(self):
        with tempfile.TemporaryDirectory() as td:
            docs = Path(td) / "docs"
            archive = docs / "archive"
            (docs / "js").mkdir(parents=True)
            (docs / "css").mkdir()
            archive.mkdir()
            (docs / "js" / "site-config.js").write_text("window.SiteConfig = {};")
            (docs / "css" / "digest.css").write_text("body{}")
            html_path = archive / "2026-07-10.html"

            html = """
            <script src="js/missing-from-archive.js?v=1"></script>
            <script src="../js/site-config.js?v=1"></script>
            <link rel="stylesheet" href="../css/digest.css?v=1">
            <script src="https://example.test/remote.js"></script>
            """

            failures = validate_digest.local_asset_failures(html, html_path)

        self.assertEqual(1, len(failures))
        self.assertIn("js/missing-from-archive.js?v=1", failures[0])


if __name__ == "__main__":
    unittest.main()
