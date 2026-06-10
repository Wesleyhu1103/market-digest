import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.update_fred as update_fred


def fred_payload():
    return {
        "updated": "2026-05-29T16:00:15Z",
        "fred": {
            "DGS2": [{"date": "2026-05-29", "value": 3.5}],
            "DGS10": [{"date": "2026-05-29", "value": 4.4}],
            "DGS30": [{"date": "2026-05-29", "value": 4.9}],
        },
        "brent": [{"date": "2026-05-29", "value": 85.0}],
        "credit": {
            "HY_OAS": [{"date": "2026-05-29", "value": 3.2}],
            "IG_OAS": [{"date": "2026-05-29", "value": 1.0}],
            "VIX": [{"date": "2026-05-29", "value": 18.0}],
            "TENMINUSTWO": [{"date": "2026-05-29", "value": -0.4}],
        },
    }


class UpdateFredTest(unittest.TestCase):
    def test_invalid_api_response_does_not_overwrite_previous_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fred-data.json"
            original = fred_payload()
            out.write_text(json.dumps(original, separators=(",", ":")))

            bad_response = json.dumps(
                {
                    "error_code": 400,
                    "error_message": "Bad Request. The value for variable api_key is not registered.",
                }
            )

            with (
                mock.patch.object(update_fred, "OUT", out),
                mock.patch.object(update_fred, "API_KEY", "bad-key"),
                mock.patch.object(update_fred, "_get", return_value=bad_response),
                mock.patch.object(update_fred.time, "sleep"),
            ):
                with self.assertRaises(SystemExit):
                    update_fred.main()

            self.assertEqual(json.loads(out.read_text()), original)


if __name__ == "__main__":
    unittest.main()
