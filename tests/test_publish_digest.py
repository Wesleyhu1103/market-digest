import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_digest import archive_safe_asset_paths  # noqa: E402


class PublishDigestTest(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_root_assets_only(self):
        html = (
            '<script src="js/site-config.js?v=1"></script>\n'
            '<link rel="stylesheet" href="css/digest.css?v=1">\n'
            '<script src="https://cdn.example/app.js"></script>\n'
            '<a href="archive/2026-07-22.html">prior</a>'
        )

        out = archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', out)
        self.assertIn('href="../css/digest.css?v=1"', out)
        self.assertIn('src="https://cdn.example/app.js"', out)
        self.assertIn('href="archive/2026-07-22.html"', out)


if __name__ == "__main__":
    unittest.main()
