import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_digest.py"


def load_publish_digest():
    spec = importlib.util.spec_from_file_location("publish_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["publish_digest"] = module
    spec.loader.exec_module(module)
    return module


class PublishDigestTests(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_assets_only(self):
        module = load_publish_digest()
        html = (
            '<script src="js/app.js?v=1"></script>'
            "<link href='css/digest.css?v=1' rel='stylesheet'>"
            '<script src="../js/already-safe.js"></script>'
            '<script src="https://cdn.example/app.js"></script>'
        )

        rewritten = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/app.js?v=1"', rewritten)
        self.assertIn("href='../css/digest.css?v=1'", rewritten)
        self.assertIn('src="../js/already-safe.js"', rewritten)
        self.assertIn('src="https://cdn.example/app.js"', rewritten)


if __name__ == "__main__":
    unittest.main()
