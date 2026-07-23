"""Vercel Hobby caps a deployment at 12 serverless functions; the 13th file
under api/ (underscore-prefixed helpers excluded) fails the WHOLE deploy.
This broke production on 2026-07-23 when api/maintenance.js became #13.
If this test fails, consolidate endpoints (see admin-proposals action=process)
instead of adding a file."""
import unittest
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"
HOBBY_FUNCTION_LIMIT = 12


class ApiFunctionLimitTest(unittest.TestCase):
    def test_function_count_within_hobby_limit(self):
        functions = sorted(
            p.name for p in API_DIR.glob("*.js") if not p.name.startswith("_")
        )
        self.assertLessEqual(
            len(functions),
            HOBBY_FUNCTION_LIMIT,
            f"{len(functions)} serverless functions exceed the Vercel Hobby "
            f"limit of {HOBBY_FUNCTION_LIMIT}; deployment will fail. "
            f"Consolidate endpoints: {functions}",
        )


if __name__ == "__main__":
    unittest.main()
