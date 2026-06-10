import unittest

from scripts import update_fred


class FredSeriesMappingTests(unittest.TestCase):
    def test_hy_oas_uses_option_adjusted_spread_series(self):
        self.assertEqual(update_fred.SERIES["HY_OAS"], "BAMLH0A0HYM2")
        self.assertNotEqual(update_fred.SERIES["HY_OAS"], "BAMLH0A0HYM2EY")


if __name__ == "__main__":
    unittest.main()
