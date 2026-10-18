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

    def test_static_rules_reject_credential_markers(self):
        import re

        module = load_validate_digest()
        rule = next(
            r for r in module.STATIC_RULES if r[0] == "no credential/env markers in public HTML"
        )
        _, pattern, expected, scope = rule
        self.assertEqual(scope, "html")
        self.assertEqual(expected, 0)
        # The shapes that actually leaked onto public June archive pages
        # (truncated token prefix + status prose), plus env-var names.
        for leaked in (
            "<p><strong>GitHub commit status:</strong> publishing with new token (ghp_aBCY...)</p>",
            "<p>New token verified working (HTTP 200).</p>",
            "<p>set GITHUB_TOKEN in Vercel production</p>",
            "<p>github_pat_11ABC is live</p>",
        ):
            self.assertTrue(re.findall(pattern, leaked, re.DOTALL | re.I), leaked)
        self.assertEqual(
            re.findall(
                pattern, "<p>Clean note; tokens of appreciation to readers.</p>", re.DOTALL | re.I
            ),
            [],
        )

    def test_static_rules_reject_direct_page_relative_fred_fetches(self):
        import re

        module = load_validate_digest()
        rule = next(
            r
            for r in module.STATIC_RULES
            if r[0] == "no page-relative fred-data.json fetch/fallback (use mdSitePath)"
        )
        _, pattern, expected, scope = rule
        self.assertEqual(scope, "js")
        self.assertEqual(expected, 0)

        for leaked in (
            "fetch('fred-data.json', { cache: 'no-store' })",
            'fetch("fred-data.json")',
            "loadFred('fred-data.json')",
            "return 'fred-data.json'",
        ):
            self.assertTrue(re.findall(pattern, leaked, re.DOTALL | re.I), leaked)

        for safe in (
            "fetch('../fred-data.json', { cache: 'no-store' })",
            "loadFred(mdSitePath('fred-data.json'))",
            "return mdSitePath('fred-data.json')",
        ):
            self.assertEqual(re.findall(pattern, safe, re.DOTALL | re.I), [], safe)


if __name__ == "__main__":
    unittest.main()
