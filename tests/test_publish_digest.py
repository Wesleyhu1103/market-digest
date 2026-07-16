import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_digest import archive_safe_asset_paths  # noqa: E402


class PublishDigestTest(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_root_assets_only(self):
        html = (
            '<script src="js/site-config.js?v=1"></script>'
            '<link rel="stylesheet" href="css/digest.css?v=1">'
            '<script src="../js/already-archive-safe.js?v=1"></script>'
            '<script src="https://cdn.example/chart.js"></script>'
        )

        self.assertEqual(
            archive_safe_asset_paths(html),
            '<script src="../js/site-config.js?v=1"></script>'
            '<link rel="stylesheet" href="../css/digest.css?v=1">'
            '<script src="../js/already-archive-safe.js?v=1"></script>'
            '<script src="https://cdn.example/chart.js"></script>',
        )


if __name__ == "__main__":
    unittest.main()
