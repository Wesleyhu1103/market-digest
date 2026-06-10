import datetime as dt
import unittest
from unittest import mock

import update_fred


class _Response:
    def __init__(self, raw: bytes):
        self._raw = raw

    def read(self) -> bytes:
        return self._raw


class UpdateFredTest(unittest.TestCase):
    def test_fetch_series_requests_csv_and_retries_timeout(self):
        today = dt.date.today().isoformat()
        response = _Response(f"observation_date,TEST\n{today},1.25\n".encode())
        requests = []

        def flaky_urlopen(req, timeout):
            requests.append((req, timeout))
            if len(requests) == 1:
                raise TimeoutError("simulated timeout")
            return response

        with mock.patch.object(update_fred.urllib.request, "urlopen", side_effect=flaky_urlopen):
            with mock.patch.object(update_fred.time, "sleep") as sleep:
                rows = update_fred.fetch_series("TEST")

        self.assertEqual(rows, [{"date": today, "value": 1.25}])
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0][1], 30)
        self.assertEqual(requests[0][0].headers["Accept"], "text/csv,*/*")
        sleep.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
