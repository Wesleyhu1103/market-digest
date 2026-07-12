"""Tests for contracts/digest-main.json loader."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from digest_contracts import (  # noqa: E402
    build_system_prompt,
    check_contract,
    load_contract,
    validate_main_rules,
    validate_static_rules,
)
from publish_digest import archive_safe_asset_paths  # noqa: E402
from validate_digest import check_local_assets  # noqa: E402


class DigestContractsTest(unittest.TestCase):
    def test_contract_loads(self):
        c = load_contract()
        self.assertEqual(c["version"], 1)
        self.assertIn("validate", c)
        self.assertIn("generate", c)

    def test_contract_sanity(self):
        self.assertEqual(check_contract(), [])

    def test_validate_rule_counts(self):
        self.assertEqual(len(validate_main_rules()), 14)
        self.assertEqual(len(validate_static_rules()), 9)

    def test_system_prompt_includes_key_rules(self):
        prompt = build_system_prompt()
        self.assertIn("chartData", prompt)
        self.assertIn("data-opt", prompt)
        self.assertIn("data-nar=\"bonds\"", prompt)
        self.assertIn("Produce ONLY a complete <main>", prompt)

    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        html = (
            '<script src="js/app.js?v=1"></script>'
            '<link href="css/site.css?v=1" rel="stylesheet">'
            '<script src="https://cdn.example/app.js"></script>'
        )
        rewritten = archive_safe_asset_paths(html)
        self.assertIn('src="../js/app.js?v=1"', rewritten)
        self.assertIn('href="../css/site.css?v=1"', rewritten)
        self.assertIn('src="https://cdn.example/app.js"', rewritten)

    def test_check_local_assets_rejects_missing_archive_relative_refs(self):
        repo = Path(__file__).resolve().parents[1]
        archive_html = repo / "docs" / "archive" / "example.html"
        html = '<script src="js/missing.js?v=1"></script><main></main>'
        self.assertFalse(check_local_assets(html, archive_html))


if __name__ == "__main__":
    unittest.main()
