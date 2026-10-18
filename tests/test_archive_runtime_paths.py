import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = ROOT / "docs" / "archive"


class ArchiveRuntimePathTests(unittest.TestCase):
    def test_archived_inline_pages_do_not_use_page_relative_runtime_paths(self):
        patterns = {
            "direct fred-data fetch": re.compile(r"fetch\(['\"]fred-data\.json['\"]"),
            "direct archive manifest fetch": re.compile(r"fetch\(['\"]archive/manifest\.json['\"]"),
            "manifest item href from archive page": re.compile(r"""href=["']["']\s*\+\s*e\.url"""),
        }
        failures = []
        for path in sorted(ARCHIVE_DIR.glob("*.html")):
            text = path.read_text()
            for label, pattern in patterns.items():
                if pattern.search(text):
                    failures.append(f"{path.relative_to(ROOT)}: {label}")

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
