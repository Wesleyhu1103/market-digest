import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_digest.py"


def load_publish_digest():
    spec = importlib.util.spec_from_file_location("publish_digest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublishDigestTests(unittest.TestCase):
    def test_archive_safe_asset_paths_rewrites_local_js_and_css(self):
        module = load_publish_digest()
        html = (
            '<script src="js/app.js?v=1"></script>'
            '<link rel="stylesheet" href="css/digest.css?v=1">'
            '<link href="css/print.css?v=1" rel="stylesheet">'
            '<script src="https://cdn.example/app.js"></script>'
        )

        out = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/app.js?v=1"', out)
        self.assertIn('href="../css/digest.css?v=1"', out)
        self.assertIn('href="../css/print.css?v=1"', out)
        self.assertIn('src="https://cdn.example/app.js"', out)


if __name__ == "__main__":
    unittest.main()
