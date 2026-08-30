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


if __name__ == "__main__":
    unittest.main()
