#!/usr/bin/env python3
"""Collect configured RSS/Atom feeds into a normalized JSON event file."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "config" / "sources.json"
OUTPUT_PATH = ROOT / "data" / "news.json"
USER_AGENT = "CryptoNewsRadar/0.1 (+https://github.com/pavel9213/crypto-news-radar)"
MAX_FEED_BYTES = 4 * 1024 * 1024
MAX_ITEMS_PER_SOURCE = 40
TIMEOUT_SECONDS = 20
ARTICLE_TIMEOUT_SECONDS = 6
MAX_ARTICLE_BYTES = 512 * 1024
MAX_IMAGE_LOOKUPS_PER_RUN = 16
IMAGE_RECHECK_DAYS = 7


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_url(url: str) -> str:
    """Remove fragments and common tracking parameters while preserving query semantics."""
    try:
        parts = urlsplit(url.strip())
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            return ""
        host = parts.netloc.lower()
        path = re.sub(r"/{2,}", "/", parts.path or "/")
        tracking = {"fbclid", "gclid", "mc_cid", "mc_eid"}
        from urllib.parse import parse_qsl, urlencode
        query = urlencode([
            (key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in tracking
        ])
        return urlunsplit((parts.scheme.lower(), host, path, query, ""))
    except ValueError:
        return ""


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, names: set[str]) -> str:
    for child in list(element):
        if local_name(child.tag) in names:
            text = " ".join(child.itertext()).strip()
            if text:
                return text
    return ""


def extract_feed_image(item: ET.Element, article_url: str) -> str:
    """Extract publisher-supplied image URLs from common RSS/Atom media fields."""
    candidates: list[tuple[int, str]] = []
    for node in item.iter():
        name = local_name(node.tag)
        if name not in {"thumbnail", "content", "enclosure", "link"}:
            continue
        mime = node.attrib.get("type", "").lower()
        rel = node.attrib.get("rel", "")
        candidate = node.attrib.get("url") or node.attrib.get("href") or ""
        if not candidate:
            continue
        if name == "link" and rel.lower() != "enclosure":
            continue
        if name in {"content", "enclosure", "link"} and not mime.startswith("image/"):
            continue
        priority = 0 if name == "thumbnail" else 1
        candidates.append((priority, candidate))
    for _, candidate in sorted(candidates, key=lambda pair: pair[0]):
        image_url = normalize_url(urljoin(article_url, candidate))
        if image_url:
            return image_url
    return ""

def parse_feed(xml_bytes: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    items: list[ET.Element] = []
    for node in root.iter():
        if local_name(node.tag) in {"item", "entry"}:
            items.append(node)

    events: list[dict[str, Any]] = []
    for item in items:
        title = clean_text(child_text(item, {"title"}))
        link = child_text(item, {"link"})
        # Atom uses href attributes instead of link text.
        if not link:
            for node in list(item):
                if local_name(node.tag) == "link":
                    rel = node.attrib.get("rel", "alternate")
                    if rel == "alternate" or not rel:
                        link = node.attrib.get("href", "")
                        if link:
                            break
        link = normalize_url(link)
        if not title or not link:
            continue
        published_raw = child_text(item, {"published", "pubdate", "date", "updated", "issued"})
        published = parse_date(published_raw)
        summary = clean_text(child_text(item, {"description", "summary", "content", "encoded"}))
        identity = link or f"{source['id']}:{title.casefold()}"
        event_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        event = {
            "id": event_id,
            "title": title[:500],
            "url": link,
            "source_id": source["id"],
            "source_name": source["name"],
            "source_trust": source.get("trust", "media"),
            "language": source.get("language", "en"),
            "topics": source.get("topics", ["other"]),
            "published_at": published,
            "summary": summary[:2000],
            "status": "unreviewed",
            "collected_at": utc_now()
        }
        image_url = extract_feed_image(item, link)
        if image_url:
            event["image_url"] = image_url
        events.append(event)
    return events




class ArticleImageParser(HTMLParser):
    """Read only image metadata from an article's HTML head."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "").strip() for key, value in attrs}
        if tag.lower() == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "")
            if content and key in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
                priority = 0 if key.startswith("og:") else 1
                self.images.append((priority, content))
        elif tag.lower() == "link" and "image_src" in values.get("rel", "").lower():
            href = values.get("href", "")
            if href:
                self.images.append((2, href))


def extract_article_image(html_bytes: bytes, article_url: str) -> str:
    """Return a normalized HTTP(S) Open Graph/Twitter image URL, if present."""
    parser = ArticleImageParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    for _, candidate in sorted(parser.images, key=lambda item: item[0]):
        image_url = normalize_url(urljoin(article_url, candidate))
        if image_url:
            parts = urlsplit(image_url)
            if parts.scheme in {"http", "https"} and parts.netloc:
                return image_url
    return ""


def fetch_article_image(article_url: str) -> str:
    """Fetch a small HTML prefix and extract its social preview image."""
    request = urllib.request.Request(
        article_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    with urllib.request.urlopen(request, timeout=ARTICLE_TIMEOUT_SECONDS) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type:
            return ""
        body = response.read(MAX_ARTICLE_BYTES + 1)
    if len(body) > MAX_ARTICLE_BYTES:
        return ""
    return extract_article_image(body, article_url)


def enrich_event_images(events: list[dict[str, Any]]) -> None:
    """Reuse cached image metadata and enrich a bounded number of new articles."""
    previous_by_id: dict[str, dict[str, Any]] = {}
    try:
        previous_payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        previous_by_id = {
            event.get("id"): event
            for event in previous_payload.get("events", [])
            if isinstance(event, dict) and event.get("id")
        }
    except (OSError, json.JSONDecodeError, AttributeError):
        pass

    now = datetime.now(timezone.utc)
    for event in events:
        previous = previous_by_id.get(event.get("id"), {})
        for field in ("image_url", "image_checked_at"):
            if previous.get(field):
                event[field] = previous[field]

    pending: list[dict[str, Any]] = []
    for event in events:
        if event.get("image_url"):
            continue
        checked_at = event.get("image_checked_at")
        if checked_at:
            try:
                checked = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
                if checked.tzinfo is None:
                    checked = checked.replace(tzinfo=timezone.utc)
                if (now - checked).total_seconds() < IMAGE_RECHECK_DAYS * 86400:
                    continue
            except (TypeError, ValueError):
                pass
        pending.append(event)

    for event in pending[:MAX_IMAGE_LOOKUPS_PER_RUN]:
        event["image_checked_at"] = utc_now()
        try:
            image_url = fetch_article_image(event["url"])
            if image_url:
                event["image_url"] = image_url
                print(f"[image] found preview for {event['source_id']}: {event['title'][:80]}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            print(f"[image] skipped {event['source_id']}: {exc}", file=sys.stderr)


class LinkCollector(HTMLParser):
    """Collect visible anchor text and hrefs from official announcement listing pages."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._anchor: dict[str, str] | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attrs_map = dict(attrs)
            href = attrs_map.get("href") or ""
            if href:
                self._anchor = {"href": href}
                self._parts = []

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor is not None:
            title = clean_text(" ".join(self._parts))
            if title:
                self.links.append({"href": self._anchor["href"], "title": title})
            self._anchor = None
            self._parts = []


def parse_html_page(html_bytes: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract only links matching a source's explicitly configured article URL pattern."""
    html = html_bytes.decode("utf-8", errors="replace")
    collector = LinkCollector()
    collector.feed(html)
    pattern = re.compile(source.get("link_pattern", r"(?!)"), re.IGNORECASE)
    base_url = source["url"]
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in collector.links:
        link = normalize_url(urljoin(base_url, item["href"]))
        title = clean_text(item["title"])
        if not link or not title or not pattern.search(link) or link in seen:
            continue
        seen.add(link)
        identity = link
        event_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        events.append({
            "id": event_id,
            "title": title[:500],
            "url": link,
            "source_id": source["id"],
            "source_name": source["name"],
            "source_trust": source.get("trust", "primary"),
            "language": source.get("language", "en"),
            "topics": source.get("topics", ["blockchain"]),
            "published_at": None,
            "summary": "",
            "status": "unreviewed",
            "collected_at": utc_now()
        })
    return events


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read(MAX_FEED_BYTES + 1)
    if len(body) > MAX_FEED_BYTES:
        raise ValueError("feed exceeded size limit")
    if not body.strip():
        raise ValueError("empty feed response")
    return body


def load_sources() -> list[dict[str, Any]]:
    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload.get("sources"), list):
        raise ValueError("config/sources.json must contain a sources array")
    return [s for s in payload["sources"] if s.get("enabled", True)]


def collect() -> dict[str, Any]:
    events_by_id: dict[str, dict[str, Any]] = {}
    source_results: list[dict[str, Any]] = []
    for source in load_sources():
        source_id = source.get("id", "unknown")
        url = source.get("url", "")
        try:
            if not normalize_url(url):
                raise ValueError("source URL must be HTTP(S)")
            body = fetch_feed(url)
            if source.get("format") == "html":
                parsed_events = parse_html_page(body, source)
                if not parsed_events and source.get("sitemap_url"):
                    try:
                        sitemap_body = fetch_feed(source["sitemap_url"])
                        sitemap_root = ET.fromstring(sitemap_body)
                        pattern = re.compile(source.get("link_pattern", r"(?!)"), re.IGNORECASE)
                        for node in sitemap_root.iter():
                            if local_name(node.tag) != "loc" or not node.text:
                                continue
                            link = normalize_url(node.text.strip())
                            if not link or not pattern.search(link):
                                continue
                            try:
                                page = fetch_feed(link).decode("utf-8", errors="replace")
                            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                                continue
                            title_match = re.search(r"<title[^>]*>(.*?)</title>", page, re.IGNORECASE | re.DOTALL)
                            title = clean_text(title_match.group(1)) if title_match else ""
                            if not title:
                                continue
                            event_id = hashlib.sha256(link.encode("utf-8")).hexdigest()[:20]
                            parsed_events.append({"id": event_id, "title": title[:500], "url": link, "source_id": source["id"], "source_name": source["name"], "source_trust": source.get("trust", "primary"), "language": source.get("language", "en"), "topics": source.get("topics", ["blockchain"]), "published_at": None, "summary": "", "status": "unreviewed", "collected_at": utc_now()})
                            if len(parsed_events) >= MAX_ITEMS_PER_SOURCE:
                                break
                    except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError, ValueError) as sitemap_exc:
                        print(f"[warn] {source_id} sitemap fallback: {sitemap_exc}", file=sys.stderr)
            else:
                parsed_events = parse_feed(body, source)
            parsed_events.sort(key=lambda event: event.get("published_at") or "", reverse=True)
            events = parsed_events[:MAX_ITEMS_PER_SOURCE]
            for event in events:
                previous = events_by_id.get(event["id"])
                if previous is None or (not previous.get("summary") and event.get("summary")):
                    events_by_id[event["id"]] = event
            source_results.append({
                "source_id": source_id,
                "ok": bool(events),
                "items": len(events),
                "items_available": len(parsed_events),
                "items_limited": len(parsed_events) > MAX_ITEMS_PER_SOURCE
            })
            print(f"[ok] {source_id}: kept {len(events)} of {len(parsed_events)} available items" if events else f"[warn] {source_id}: no article links extracted", file=None if events else sys.stderr)
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError, ValueError) as exc:
            source_results.append({"source_id": source_id, "ok": False, "error": str(exc)[:300]})
            print(f"[warn] {source_id}: {exc}", file=sys.stderr)

    events = list(events_by_id.values())
    events.sort(key=lambda event: event.get("published_at") or "", reverse=True)
    enrich_event_images(events)
    payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "event_count": len(events),
        "source_count": len(source_results),
        "sources": source_results,
        "events": events
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(OUTPUT_PATH)
    return payload


if __name__ == "__main__":
    result = collect()
    failed = sum(1 for source in result["sources"] if not source["ok"])
    print(f"Collected {result['event_count']} events from {result['source_count']} sources; {failed} source(s) failed.")
    # Partial source failure is non-fatal; total failure is signalled to CI.
    if result["source_count"] and failed == result["source_count"]:
        sys.exit(1)
