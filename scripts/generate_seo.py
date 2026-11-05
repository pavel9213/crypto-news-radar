#!/usr/bin/env python3
"""Generate crawlable static story pages, sitemap.xml and robots.txt for GitHub Pages."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import format_datetime
import html
import json
import re
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://pavel9213.github.io/crypto-news-radar/"
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


def safe_http_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not re.match(r"^https?://", value, re.IGNORECASE):
        return ""
    return value


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def make_description(event: dict) -> str:
    summary = clean_text(event.get("summary"))
    title = clean_text(event.get("title"))
    description = summary or f"{title} — the latest update tracked by Crypto News Radar."
    if len(description) > 160:
        description = description[:157].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return description


def iso_value(value: object) -> str:
    value = clean_text(value)
    if not value:
        return ""
    try:
        from datetime import datetime
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.isoformat()
    except ValueError:
        return ""


def parse_datetime(value: object) -> datetime | None:
    normalized = iso_value(value)
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def rss_date(value: object) -> str:
    parsed = parse_datetime(value)
    return format_datetime(parsed) if parsed else ""


def rss_feed(events: list[dict]) -> bytes:
    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "Crypto News Radar"
    ET.SubElement(channel, "link").text = SITE_URL
    ET.SubElement(channel, "description").text = (
        "Independent crypto news, blockchain updates, DeFi research and Web3 signals."
    )
    ET.SubElement(channel, "language").text = "en"
    build_dates = [
        parse_datetime(event.get("collected_at") or event.get("published_at"))
        for event in events if isinstance(event, dict)
    ]
    build_dates = [value for value in build_dates if value]
    if build_dates:
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(max(build_dates))

    valid_events = [
        event for event in events
        if isinstance(event, dict) and ID_PATTERN.fullmatch(clean_text(event.get("id")))
    ]
    valid_events.sort(
        key=lambda event: parse_datetime(event.get("published_at") or event.get("collected_at"))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    for event in valid_events[:50]:
        story_id = clean_text(event.get("id"))
        story_url = SITE_URL + "stories/" + quote(story_id, safe="") + ".html"
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = clean_text(event.get("title")) or "Crypto news update"
        ET.SubElement(item, "link").text = story_url
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = story_url
        published = rss_date(event.get("published_at") or event.get("collected_at"))
        if published:
            ET.SubElement(item, "pubDate").text = published
        ET.SubElement(item, "description").text = clean_text(event.get("summary")) or make_description(event)
        source = clean_text(event.get("source_name"))
        original_url = safe_http_url(event.get("url"))
        if source and original_url:
            ET.SubElement(item, "source", {"url": original_url}).text = source
        topics = event.get("topics") if isinstance(event.get("topics"), list) else []
        for topic in topics:
            cleaned_topic = clean_text(topic)
            if cleaned_topic:
                ET.SubElement(item, "category").text = cleaned_topic

    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def article_html(event: dict) -> str:
    story_id = clean_text(event.get("id"))
    if not ID_PATTERN.fullmatch(story_id):
        raise ValueError(f"Unsafe or missing story id: {story_id!r}")

    title = clean_text(event.get("title")) or "Crypto news update"
    description = make_description(event)
    source = clean_text(event.get("source_name")) or "News source"
    published = iso_value(event.get("published_at") or event.get("collected_at"))
    collected = iso_value(event.get("collected_at"))
    original_url = safe_http_url(event.get("url"))
    image_url = safe_http_url(event.get("image_url"))
    language = clean_text(event.get("language")) or "en"
    topics = event.get("topics") if isinstance(event.get("topics"), list) else []
    topics = [clean_text(topic) for topic in topics if clean_text(topic)]
    canonical = SITE_URL + "stories/" + quote(story_id, safe="") + ".html"

    e = html.escape
    tags_html = "".join(f'<span class="article-tag">{e(topic)}</span>' for topic in topics)
    image_html = (
        f'<figure class="article-hero-image"><img src="{e(image_url)}" alt="{e(title)}" '
        'loading="eager" decoding="async" referrerpolicy="no-referrer">'
        f'<figcaption>Image provided by {e(source)}</figcaption></figure>'
        if image_url else
        '<div class="article-image-fallback"><span>CRYPTO NEWS RADAR</span></div>'
    )
    summary_html = e(clean_text(event.get("summary")) or description)
    original_html = (
        f'<a href="{e(original_url)}" target="_blank" rel="noopener noreferrer">Read original report ↗</a>'
        if original_url else "<span>Original link unavailable</span>"
    )

    structured = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "headline": title,
        "description": description,
        "inLanguage": language,
        "publisher": {"@type": "Organization", "name": "Crypto News Radar", "url": SITE_URL},
        "isAccessibleForFree": True,
    }
    if published:
        structured["datePublished"] = published
    if collected:
        structured["dateModified"] = collected
    if image_url:
        structured["image"] = [image_url]
    if topics:
        structured["articleSection"] = topics
    json_ld = json.dumps(structured, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    twitter_card = "summary_large_image" if image_url else "summary"
    image_meta = (
        f'<meta property="og:image" content="{e(image_url)}">\n'
        f'  <meta property="og:image:alt" content="{e(title)}">\n'
        f'  <meta name="twitter:image" content="{e(image_url)}">\n'
        if image_url else ""
    )

    return f"""<!doctype html>
<html lang="{e(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#ffffff">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <title>{e(title)} | Crypto News Radar</title>
  <meta name="description" content="{e(description)}">
  <link rel="canonical" href="{e(canonical)}">
  <link rel="alternate" type="application/rss+xml" title="Crypto News Radar RSS" href="{SITE_URL}feed.xml">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Crypto News Radar">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(description)}">
  <meta property="og:url" content="{e(canonical)}">
  {image_meta.rstrip()}
  <meta name="twitter:card" content="{twitter_card}">
  <meta name="twitter:title" content="{e(title)}">
  <meta name="twitter:description" content="{e(description)}">
  <script type="application/ld+json">{json_ld}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../styles.css">
</head>
<body class="article-page">
  <div class="edition-bar"><div class="container edition-inner"><span>INDEPENDENT CRYPTO NEWS &amp; RESEARCH</span><span>THE RADAR STORY DESK</span><span class="edition-live"><i></i> LIVE RADAR</span></div></div>
  <header class="topbar">
    <div class="container topbar-inner">
      <a class="brand" href="../" aria-label="Crypto News Radar home"><span class="brand-mark">CR</span><span class="brand-name">CRYPTO<span>NEWS RADAR</span></span></a>
      <nav class="main-nav" aria-label="Main navigation"><a href="../">Home</a><a href="../#news">Latest news</a><a href="../#project-monitor">Projects</a></nav>
      <div class="header-status"><span class="live-dot"></span><span>STORY VIEW</span></div>
    </div>
  </header>
  <main class="container article-main">
    <a class="article-back" href="../">← Back to Crypto News Radar</a>
    <article class="article-content">
      <div class="article-kicker"><span>CRYPTO NEWS RADAR / STORY</span><span>{'Primary source' if event.get('source_trust') == 'primary' else 'Media report'}</span></div>
      <div class="article-tags">{tags_html}</div>
      <h1>{e(title)}</h1>
      <div class="article-byline"><strong>{e(source)}</strong><span>{e(published or 'Date unavailable')}</span></div>
      {image_html}
      <div class="article-summary"><span>THE STORY</span><p>{summary_html}</p></div>
      <div class="article-source-box"><div><span>ORIGINAL PUBLICATION</span><strong>{e(source)}</strong></div>{original_html}</div>
      <p class="article-disclaimer">Crypto News Radar aggregates headlines and available publisher summaries. This page does not reproduce the full original article. Verify important claims with the publisher and primary sources. Not financial advice.</p>
    </article>
  </main>
  <footer><div class="container footer-inner"><span class="footer-brand">CRYPTO NEWS RADAR</span><span>Built in public · Open-source project</span><a href="https://github.com/pavel9213/crypto-news-radar">View on GitHub ↗</a></div></footer>
</body>
</html>
"""


def generate(output_dir: Path) -> tuple[int, int]:
    data_path = ROOT / "data" / "news.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    stories_dir = output_dir / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)

    urls = [SITE_URL]
    sitemap_rows = [
        "<url><loc>" + html.escape(SITE_URL) + "</loc></url>"
    ]
    generated = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        story_id = clean_text(event.get("id"))
        if not ID_PATTERN.fullmatch(story_id):
            continue
        page_url = SITE_URL + "stories/" + quote(story_id, safe="") + ".html"
        (stories_dir / f"{story_id}.html").write_text(article_html(event), encoding="utf-8")
        lastmod = iso_value(event.get("collected_at") or event.get("published_at"))
        lastmod_tag = f"<lastmod>{html.escape(lastmod[:10])}</lastmod>" if lastmod else ""
        sitemap_rows.append(f"<url><loc>{html.escape(page_url)}</loc>{lastmod_tag}</url>")
        urls.append(page_url)
        generated += 1

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n' + (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(sitemap_rows)
        + "\n</urlset>\n"
    )
    ET.fromstring(sitemap)
    (output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (output_dir / "feed.xml").write_bytes(rss_feed(events))
    (output_dir / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: " + SITE_URL + "sitemap.xml\n",
        encoding="utf-8",
    )
    return generated, len(urls)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    count, urls = generate(args.output)
    print(f"Generated {count} static story pages, a sitemap with {urls} URLs, and an RSS feed.")


if __name__ == "__main__":
    main()
