import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "feed_sources.py"


def load_feed_sources():
    import sys

    spec = importlib.util.spec_from_file_location("feed_sources", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["feed_sources"] = module
    spec.loader.exec_module(module)
    return module


class FeedSourcesTests(unittest.TestCase):
    def test_parse_rss_items(self):
        module = load_feed_sources()
        xml = b"""<?xml version='1.0'?>
        <rss><channel>
          <item>
            <title>Test headline</title>
            <description><![CDATA[<p>Body text</p>]]></description>
            <pubDate>Fri, 12 Jun 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""
        items = module._parse_items(xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Test headline")
        self.assertIn("Body text", items[0].desc)

    def test_parse_atom_entries(self):
        module = load_feed_sources()
        xml = b"""<?xml version='1.0'?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Atom headline</title>
            <summary>Atom summary</summary>
            <published>2026-06-12T10:00:00Z</published>
          </entry>
        </feed>"""
        items = module._parse_items(xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Atom headline")

    def test_freshness_filter(self):
        module = load_feed_sources()
        now = datetime.now(timezone.utc)
        fresh = module.FeedItem("new", "x", "", now, "")
        old = module.FeedItem("old", "x", "", now - timedelta(hours=48), "")
        cutoff = now - timedelta(hours=module.FRESH_HOURS)
        self.assertTrue(module._is_fresh(fresh, cutoff))
        self.assertFalse(module._is_fresh(old, cutoff))

    def test_build_sources_html_lists_worked_and_failed(self):
        module = load_feed_sources()
        reports = [
            module.FeedResult("Bloomberg Markets", "http://x", "ok", 30, 12, "2026-06-12 09:00 ET"),
            module.FeedResult("CoinDesk", "http://y", "failed", 0, 0, error="timeout"),
        ]
        html_out = module.build_sources_html(reports, datetime(2026, 6, 12, 9, 0))
        self.assertIn("Bloomberg Markets", html_out)
        self.assertIn("CoinDesk", html_out)
        self.assertIn("estimated from headlines", html_out)

    def test_inject_sources_section_replaces_existing(self):
        module = load_feed_sources()
        main_html = "<main><section id='sources'><p>old</p></section></main>"
        new = module.inject_sources_section(main_html, "<section id='sources'><p>new</p></section>")
        self.assertIn("<p>new</p>", new)
        self.assertNotIn("<p>old</p>", new)

    def test_calculated_risk_not_in_feed_list(self):
        module = load_feed_sources()
        self.assertNotIn("Calculated Risk", module.FEEDS)

    def test_new_feeds_present(self):
        module = load_feed_sources()
        self.assertIn("Matt Levine Money Stuff", module.FEEDS)
        self.assertIn("CoinDesk", module.FEEDS)


if __name__ == "__main__":
    unittest.main()
