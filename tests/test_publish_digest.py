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
    def test_archive_safe_asset_paths_rewrites_local_root_assets(self):
        module = load_publish_digest()
        html = """<!doctype html>
<script src="js/site-config.js?v=1"></script>
<script src="https://cdn.example/chart.js"></script>
<link rel="stylesheet" href="css/digest.css?v=1">
<link href="css/print.css" rel="stylesheet">
<link rel="icon" href="css/not-a-stylesheet.ico">
<main></main>"""

        rewritten = module.archive_safe_asset_paths(html)

        self.assertIn('src="../js/site-config.js?v=1"', rewritten)
        self.assertIn('src="https://cdn.example/chart.js"', rewritten)
        self.assertIn('href="../css/digest.css?v=1"', rewritten)
        self.assertIn('href="../css/print.css"', rewritten)
        self.assertIn('href="css/not-a-stylesheet.ico"', rewritten)


if __name__ == "__main__":
    unittest.main()
