import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
update_fred = importlib.import_module("update_fred")


POINT = [{"date": "2026-06-09", "value": 1.23}]
PREVIOUS = {
    "fred": {
        "DGS2": [{"date": "2026-06-06", "value": 2.0}],
        "DGS10": [{"date": "2026-06-06", "value": 10.0}],
        "DGS30": [{"date": "2026-06-06", "value": 30.0}],
    },
    "brent": [{"date": "2026-06-06", "value": 70.0}],
    "credit": {
        "HY_OAS": [{"date": "2026-06-06", "value": 3.5}],
        "IG_OAS": [{"date": "2026-06-06", "value": 0.8}],
        "VIX": [{"date": "2026-06-06", "value": 20.0}],
        "TENMINUSTWO": [{"date": "2026-06-06", "value": 0.4}],
    },
}


class UpdateFredTests(unittest.TestCase):
    def test_hy_oas_uses_spread_series_not_effective_yield(self):
        self.assertEqual(update_fred.SERIES["HY_OAS"], "BAMLH0A0HYM2")

    def test_empty_fetch_keeps_previous_series_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fred-data.json"
            out.write_text(json.dumps(PREVIOUS))
            responses = {sid: [dict(POINT[0], value=i)] for i, sid in enumerate(update_fred.SERIES.values(), 1)}
            responses["DGS10"] = []

            with (
                patch.object(update_fred, "OUT", out),
                patch.object(update_fred, "API_KEY", "test-key"),
                patch.object(update_fred, "fetch_series", side_effect=lambda sid: responses[sid]),
            ):
                update_fred.main()

            payload = json.loads(out.read_text())
            self.assertEqual(payload["fred"]["DGS10"], PREVIOUS["fred"]["DGS10"])
            self.assertEqual(payload["fred"]["DGS2"], responses["DGS2"])

    def test_all_empty_fetches_leave_existing_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fred-data.json"
            original = json.dumps(PREVIOUS)
            out.write_text(original)

            with (
                patch.object(update_fred, "OUT", out),
                patch.object(update_fred, "API_KEY", "test-key"),
                patch.object(update_fred, "fetch_series", return_value=[]),
            ):
                with self.assertRaises(SystemExit):
                    update_fred.main()

            self.assertEqual(out.read_text(), original)


if __name__ == "__main__":
    unittest.main()
