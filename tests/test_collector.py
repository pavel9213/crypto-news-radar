import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_news.py"
SPEC = importlib.util.spec_from_file_location("collect_news", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class CollectorTests(unittest.TestCase):
    def test_normalize_url_removes_tracking_and_fragment(self):
        self.assertEqual(
            collector.normalize_url("https://Example.com/story?utm_source=x&id=4#section"),
            "https://example.com/story?id=4",
        )

    def test_rejects_non_http_urls(self):
        self.assertEqual(collector.normalize_url("javascript:alert(1)"), "")
        self.assertEqual(collector.normalize_url("mailto:test@example.com"), "")

    def test_parse_rss_item(self):
        xml = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><item>
          <title>Protocol upgrade announced</title>
          <link>https://example.org/post?utm_medium=rss</link>
          <pubDate>Tue, 27 Oct 2026 10:00:00 GMT</pubDate>
          <description>A useful update</description>
        </item></channel></rss>"""
        source = {"id": "example", "name": "Example", "topics": ["blockchain"], "language": "en", "trust": "primary"}
        events = collector.parse_feed(xml, source)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Protocol upgrade announced")
        self.assertEqual(events[0]["url"], "https://example.org/post")
        self.assertEqual(events[0]["published_at"], "2026-10-27T10:00:00+00:00")

    def test_parse_atom_link_attribute(self):
        xml = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
          <title>Research paper</title><link href="https://example.org/research" rel="alternate"/>
          <updated>2026-10-27T10:00:00Z</updated><summary>Abstract</summary>
        </entry></feed>"""
        events = collector.parse_feed(xml, {"id": "lab", "name": "Lab", "topics": ["research"]})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["url"], "https://example.org/research")
        self.assertEqual(events[0]["summary"], "Abstract")

    def test_invalid_date_is_unknown_not_guessed(self):
        self.assertIsNone(collector.parse_date("not-a-date"))


if __name__ == "__main__":
    unittest.main()
