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

    def test_extracts_rss_media_thumbnail(self):
        xml = b"""<rss><channel><item><title>Story</title><link>https://example.org/story</link>
        <media:thumbnail xmlns:media="http://search.yahoo.com/mrss/" url="/images/thumb.jpg" />
        </item></channel></rss>"""
        item = collector.ET.fromstring(xml).find("./channel/item")
        self.assertEqual(collector.extract_feed_image(item, "https://example.org/story"), "https://example.org/images/thumb.jpg")

    def test_extracts_atom_image_enclosure(self):
        xml = b"""<entry xmlns="http://www.w3.org/2005/Atom"><link rel="enclosure" type="image/jpeg" href="https://example.org/cover.jpg" /></entry>"""
        item = collector.ET.fromstring(xml)
        self.assertEqual(collector.extract_feed_image(item, "https://example.org/story"), "https://example.org/cover.jpg")

    def test_ignores_non_image_enclosures(self):
        xml = b"""<entry><enclosure type="audio/mpeg" url="https://example.org/audio.mp3" /></entry>"""
        item = collector.ET.fromstring(xml)
        self.assertEqual(collector.extract_feed_image(item, "https://example.org/story"), "")

    def test_extracts_open_graph_image_and_resolves_relative_url(self):
        html = b'<html><head><meta property="og:image" content="/images/cover.jpg"></head></html>'
        self.assertEqual(
            collector.extract_article_image(html, "https://example.org/story"),
            "https://example.org/images/cover.jpg",
        )

    def test_prefers_open_graph_image_to_twitter_image(self):
        html = b'<meta name="twitter:image" content="https://example.org/twitter.jpg"><meta property="og:image" content="https://example.org/og.jpg">'
        self.assertEqual(
            collector.extract_article_image(html, "https://example.org/story"),
            "https://example.org/og.jpg",
        )

    def test_ignores_non_http_image_urls(self):
        html = b'<meta property="og:image" content="javascript:alert(1)">'
        self.assertEqual(collector.extract_article_image(html, "https://example.org/story"), "")

    def test_invalid_date_is_unknown_not_guessed(self):
        self.assertIsNone(collector.parse_date("not-a-date"))


if __name__ == "__main__":
    unittest.main()
