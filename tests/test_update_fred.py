import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_fred.py"


def load_update_fred():
    spec = importlib.util.spec_from_file_location("update_fred", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_previous(module):
    return {
        key: [{"date": "2026-01-01", "value": idx}]
        for idx, key in enumerate(module.SERIES, start=1)
    }


class UpdateFredTests(unittest.TestCase):
    def test_hy_oas_uses_option_adjusted_spread_series(self):
        module = load_update_fred()

        self.assertEqual(module.SERIES["HY_OAS"], "BAMLH0A0HYM2")
        self.assertNotEqual(module.SERIES["HY_OAS"], "BAMLH0A0HYM2EY")

    def test_successful_but_invalid_responses_parse_as_empty_rows(self):
        module = load_update_fred()

        module.API_KEY = "dummy"
        module._get = lambda url: '{"error_code":400,"error_message":"Bad request"}'
        self.assertEqual(module.fetch_series("DGS2"), [])

        module.API_KEY = ""
        module._get = lambda url: "<html><body>not csv</body></html>"
        self.assertEqual(module.fetch_series("DGS2"), [])

    def test_fred_requests_advertise_parseable_response_types(self):
        module = load_update_fred()
        seen = {}

        class Response:
            def read(self):
                return b"DATE,DGS2\n2026-06-10,4.2\n"

        def fake_urlopen(request, timeout):
            seen["accept"] = request.get_header("Accept")
            seen["user_agent"] = request.get_header("User-agent")
            return Response()

        with mock.patch.object(module.urllib.request, "urlopen", fake_urlopen):
            body = module._get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2")

        self.assertIn("text/csv", seen["accept"])
        self.assertIn("application/json", seen["accept"])
        self.assertTrue(seen["user_agent"])
        self.assertIn("DGS2", body)

    def test_empty_fetches_abort_without_touching_output(self):
        module = load_update_fred()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fred-data.json"
            original = '{"unchanged":true}'
            out.write_text(original)

            module.OUT = out
            module.API_KEY = ""
            module.load_previous = lambda: sample_previous(module)
            module.fetch_series = lambda series_id: []

            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    module.main()

            self.assertIn("no FRED series fetched", str(raised.exception))
            self.assertEqual(out.read_text(), original)

    def test_empty_series_preserves_previous_when_other_series_fetch(self):
        module = load_update_fred()
        previous = sample_previous(module)
        fresh = [{"date": "2026-06-10", "value": 4.25}]

        with tempfile.TemporaryDirectory() as tmp:
            module.OUT = Path(tmp) / "fred-data.json"
            module.API_KEY = "dummy"
            module.load_previous = lambda: previous

            def fake_fetch(series_id):
                if series_id == module.SERIES["DGS10"]:
                    return []
                return fresh

            module.fetch_series = fake_fetch
            with contextlib.redirect_stdout(io.StringIO()):
                module.main()

            written = json.loads(module.OUT.read_text())
            self.assertEqual(written["fred"]["DGS2"], fresh)
            self.assertEqual(written["fred"]["DGS10"], previous["DGS10"])
            self.assertEqual(written["fred"]["DGS30"], fresh)
            self.assertEqual(written["brent"], fresh)
            self.assertEqual(written["credit"]["HY_OAS"], fresh)


if __name__ == "__main__":
    unittest.main()
