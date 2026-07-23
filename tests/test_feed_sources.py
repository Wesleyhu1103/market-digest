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
        fresh = module.FeedItem(title="new", url="x", desc="", published=now, published_label="")
        old = module.FeedItem(
            title="old", url="x", desc="", published=now - timedelta(hours=48), published_label=""
        )
        undated = module.FeedItem(title="undated", url="x", desc="", published=None, published_label="")
        cutoff = now - timedelta(hours=module.FRESH_HOURS)
        self.assertTrue(module._is_fresh(fresh, cutoff))
        self.assertFalse(module._is_fresh(old, cutoff))
        # Undated items never count as fresh (they can't satisfy the
        # MIN_TOTAL_FRESH_ITEMS gate) but fetch_feed may still carry them
        # along as source material — see the policy tests below.
        self.assertFalse(module._is_fresh(undated, cutoff))

    @staticmethod
    def _rss(items_xml: str) -> bytes:
        return f"<?xml version='1.0'?><rss><channel>{items_xml}</channel></rss>".encode()

    @staticmethod
    def _item(title: str, pub: str | None) -> str:
        pub_xml = f"<pubDate>{pub}</pubDate>" if pub else ""
        return f"<item><title>{title}</title><link>http://x/{title}</link>{pub_xml}</item>"

    def test_fetch_feed_undated_policy(self):
        module = load_feed_sources()
        now = datetime.now(timezone.utc)
        fresh_pub = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        old_pub = (now - timedelta(hours=90)).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # fresh dated + undated: undated ride along but are not counted fresh
        xml = self._rss(self._item("a", fresh_pub) + self._item("b", None))
        with mock.patch.object(module, "_fetch_bytes", return_value=xml):
            items, rep = module.fetch_feed("t", "http://t")
        self.assertEqual(rep.status, "ok")
        self.assertEqual(rep.items_fresh, 1)
        self.assertEqual(rep.items_undated, 1)
        self.assertEqual(len(items), 2)

        # fully undated feed: capped items kept, status 'undated', 0 fresh
        xml = self._rss("".join(self._item(f"u{i}", None) for i in range(10)))
        with mock.patch.object(module, "_fetch_bytes", return_value=xml):
            items, rep = module.fetch_feed("t", "http://t")
        self.assertEqual(rep.status, "undated")
        self.assertEqual(rep.items_fresh, 0)
        self.assertEqual(len(items), module.MAX_UNDATED_PER_FEED)

        # stale feed: its undated items are dropped with it
        xml = self._rss(self._item("old", old_pub) + self._item("u", None))
        with mock.patch.object(module, "_fetch_bytes", return_value=xml):
            items, rep = module.fetch_feed("t", "http://t")
        self.assertEqual(rep.status, "stale")
        self.assertEqual(items, [])

    def test_build_sources_html_lists_worked_and_failed(self):
        module = load_feed_sources()
        reports = [
            module.FeedResult("Bloomberg Markets", "http://x", "ok", 30, 12, newest="2026-06-12 09:00 ET"),
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
