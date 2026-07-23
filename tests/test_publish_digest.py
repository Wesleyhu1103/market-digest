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
    def test_archive_safe_asset_paths_rewrites_local_root_assets_only(self):
        module = load_publish_digest()

        html = (
            '<script src="js/digest-ui.js?v=1"></script>'
            '<link rel="stylesheet" href="css/digest.css?v=1">'
            '<script src="https://cdn.example/app.js"></script>'
            '<link href="https://fonts.example/css?family=x" rel="stylesheet">'
        )

        out = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/digest-ui.js?v=1"', out)
        self.assertIn('href="../css/digest.css?v=1"', out)
        self.assertIn('src="https://cdn.example/app.js"', out)
        self.assertIn('href="https://fonts.example/css?family=x"', out)


if __name__ == "__main__":
    unittest.main()
