#!/usr/bin/env python3
"""Collect configured RSS/Atom feeds into a normalized JSON event file."""

from __future__ import annotations

import hashlib
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
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "config" / "sources.json"
OUTPUT_PATH = ROOT / "data" / "news.json"
USER_AGENT = "CryptoNewsRadar/0.1 (+https://github.com/pavel9213/crypto-news-radar)"
MAX_FEED_BYTES = 4 * 1024 * 1024
MAX_ITEMS_PER_SOURCE = 40
TIMEOUT_SECONDS = 20


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
        events.append({
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
        })
    return events


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
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
            parsed_events = parse_feed(fetch_feed(url), source)
            parsed_events.sort(key=lambda event: event.get("published_at") or "", reverse=True)
            events = parsed_events[:MAX_ITEMS_PER_SOURCE]
            for event in events:
                previous = events_by_id.get(event["id"])
                if previous is None or (not previous.get("summary") and event.get("summary")):
                    events_by_id[event["id"]] = event
            source_results.append({
                "source_id": source_id,
                "ok": True,
                "items": len(events),
                "items_available": len(parsed_events),
                "items_limited": len(parsed_events) > MAX_ITEMS_PER_SOURCE
            })
            print(f"[ok] {source_id}: kept {len(events)} of {len(parsed_events)} available items")
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError, ValueError) as exc:
            source_results.append({"source_id": source_id, "ok": False, "error": str(exc)[:300]})
            print(f"[warn] {source_id}: {exc}", file=sys.stderr)

    events = list(events_by_id.values())
    events.sort(key=lambda event: event.get("published_at") or "", reverse=True)
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
