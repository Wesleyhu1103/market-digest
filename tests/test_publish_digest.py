import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_digest import archive_safe_asset_paths  # noqa: E402


class PublishDigestTest(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        html = (
            '<script src="js/site-config.js?v=20260710"></script>\n'
            '<link rel="stylesheet" href="css/digest.css?v=20260710">\n'
            '<script src="https://cdn.example/chart.js"></script>\n'
            '<a href="https://example.com/story">Source</a>\n'
            '<a href="../index.html">Back</a>\n'
        )

        rewritten = archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=20260710"', rewritten)
        self.assertIn('href="../css/digest.css?v=20260710"', rewritten)
        self.assertIn('src="https://cdn.example/chart.js"', rewritten)
        self.assertIn('href="https://example.com/story"', rewritten)
        self.assertIn('href="../index.html"', rewritten)
        self.assertNotIn('src="js/', rewritten)
        self.assertNotIn('href="css/', rewritten)


if __name__ == "__main__":
    unittest.main()
