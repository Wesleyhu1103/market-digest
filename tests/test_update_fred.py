import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.update_fred as update_fred


SAMPLE_POINT = [{"date": "2026-06-09", "value": 4.25}]


def previous_payload():
    return {
        "updated": "2026-06-01T00:00:00Z",
        "fred": {
            "DGS2": [{"date": "2026-06-01", "value": 3.9}],
            "DGS10": [{"date": "2026-06-01", "value": 4.4}],
            "DGS30": [{"date": "2026-06-01", "value": 4.9}],
        },
        "brent": [{"date": "2026-06-01", "value": 65.0}],
        "credit": {
            "HY_OAS": [{"date": "2026-06-01", "value": 2.8}],
            "IG_OAS": [{"date": "2026-06-01", "value": 0.75}],
            "VIX": [{"date": "2026-06-01", "value": 18.0}],
            "TENMINUSTWO": [{"date": "2026-06-01", "value": 0.5}],
        },
    }


class UpdateFredFallbackTests(unittest.TestCase):
    def setUp(self):
        self.original_out = update_fred.OUT
        self.original_fetch_series = update_fred.fetch_series

    def tearDown(self):
        update_fred.OUT = self.original_out
        update_fred.fetch_series = self.original_fetch_series

    def test_empty_series_keeps_previous_values(self):
        previous = previous_payload()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "fred-data.json"
            out.write_text(json.dumps(previous))
            update_fred.OUT = out

            def fake_fetch(series_id):
                if series_id == "DGS2":
                    return []
                return copy.deepcopy(SAMPLE_POINT)

            update_fred.fetch_series = fake_fetch
            with contextlib.redirect_stdout(io.StringIO()):
                update_fred.main()

            payload = json.loads(out.read_text())
            self.assertEqual(payload["fred"]["DGS2"], previous["fred"]["DGS2"])
            self.assertEqual(payload["fred"]["DGS10"], SAMPLE_POINT)
            self.assertEqual(payload["brent"], SAMPLE_POINT)
            self.assertEqual(payload["credit"]["VIX"], SAMPLE_POINT)

    def test_all_empty_series_abort_without_overwriting_previous_file(self):
        previous = previous_payload()
        original_text = json.dumps(previous)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "fred-data.json"
            out.write_text(original_text)
            update_fred.OUT = out
            update_fred.fetch_series = lambda _series_id: []

            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    update_fred.main()

            self.assertEqual(out.read_text(), original_text)


if __name__ == "__main__":
    unittest.main()
