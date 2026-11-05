import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_seo.py"
SPEC = importlib.util.spec_from_file_location("generate_seo", SCRIPT)
seo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seo)


class SeoGenerationTests(unittest.TestCase):
    def test_article_has_unique_social_metadata_and_structured_data(self):
        event = {
            "id": "abc123",
            "title": "A <strong>crypto</strong> headline",
            "summary": "A useful summary for social previews.",
            "url": "https://example.org/story",
            "source_name": "Example News",
            "source_trust": "primary",
            "language": "en",
            "topics": ["defi", "security"],
            "published_at": "2026-11-04T12:00:00+00:00",
            "collected_at": "2026-11-04T12:05:00+00:00",
            "image_url": "https://example.org/cover.jpg",
        }
        page = seo.article_html(event)
        self.assertIn('<meta property="og:type" content="article">', page)
        self.assertIn('name="twitter:card" content="summary_large_image"', page)
        self.assertIn('rel="canonical" href="https://pavel9213.github.io/crypto-news-radar/stories/abc123.html"', page)
        self.assertIn("&lt;strong&gt;", page)
        self.assertNotIn("<strong>crypto</strong>", page)
        marker = '<script type="application/ld+json">'
        structured = page.split(marker, 1)[1].split("</script>", 1)[0]
        parsed = json.loads(structured)
        self.assertEqual(parsed["@type"], "NewsArticle")
        self.assertEqual(parsed["headline"], "A <strong>crypto</strong> headline")
        self.assertEqual(parsed["image"], ["https://example.org/cover.jpg"])

    def test_article_without_image_uses_summary_card(self):
        page = seo.article_html({"id": "noimage", "title": "No image", "url": "https://example.org"})
        self.assertIn('name="twitter:card" content="summary"', page)
        self.assertNotIn('property="og:image"', page)

    def test_rejects_unsafe_story_ids(self):
        with self.assertRaises(ValueError):
            seo.article_html({"id": "../escape", "title": "Unsafe"})

    def test_generates_story_pages_sitemap_and_robots(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            data_dir = seo.ROOT / "data"
            original = data_dir / "news.json"
            original_content = original.read_text(encoding="utf-8")
            try:
                original.write_text(json.dumps({"events": [
                    {"id": "story001", "title": "Story one", "url": "https://example.org/one"},
                    {"id": "story002", "title": "Story two", "url": "https://example.org/two"},
                ]}), encoding="utf-8")
                count, urls = seo.generate(output)
            finally:
                original.write_text(original_content, encoding="utf-8")
            self.assertEqual((count, urls), (2, 3))
            self.assertTrue((output / "stories" / "story001.html").exists())
            self.assertIn("sitemap.xml", (output / "robots.txt").read_text(encoding="utf-8"))
            root = ET.parse(output / "sitemap.xml").getroot()
            self.assertEqual(len(root), 3)


if __name__ == "__main__":
    unittest.main()
