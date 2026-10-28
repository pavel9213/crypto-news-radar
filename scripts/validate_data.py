#!/usr/bin/env python3
"""Validate source configuration and generated news data without third-party packages."""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def valid_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def validate_sources() -> list[str]:
    path = ROOT / "config" / "sources.json"
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"sources config cannot be read: {exc}"]
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["sources config must contain a non-empty sources array"]
    ids: set[str] = set()
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be an object")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", source_id):
            errors.append(f"{label}.id must be a lowercase slug")
        elif source_id in ids:
            errors.append(f"duplicate source id: {source_id}")
        else:
            ids.add(source_id)
        if not source.get("name"):
            errors.append(f"{label}.name is required")
        if not valid_http_url(source.get("url")):
            errors.append(f"{label}.url must be HTTP(S)")
        if not isinstance(source.get("topics"), list) or not source["topics"]:
            errors.append(f"{label}.topics must be a non-empty list")
    return errors


def validate_news() -> list[str]:
    path = ROOT / "data" / "news.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"news data cannot be read: {exc}"]
    errors: list[str] = []
    events = payload.get("events")
    if not isinstance(events, list):
        return ["news data must contain an events array"]
    seen_ids: set[str] = set()
    for index, event in enumerate(events):
        label = f"events[{index}]"
        if not isinstance(event, dict):
            errors.append(f"{label} must be an object")
            continue
        for field in ("id", "title", "url", "source_id", "source_name"):
            if not event.get(field):
                errors.append(f"{label}.{field} is required")
        if event.get("id") in seen_ids:
            errors.append(f"duplicate event id: {event.get('id')}")
        seen_ids.add(event.get("id"))
        if not valid_http_url(event.get("url")):
            errors.append(f"{label}.url must be HTTP(S)")
        if not isinstance(event.get("topics"), list):
            errors.append(f"{label}.topics must be a list")
    return errors


if __name__ == "__main__":
    problems = validate_sources() + validate_news()
    if problems:
        print("\n".join(f"ERROR: {problem}" for problem in problems))
        sys.exit(1)
    print("Source registry and available news data are valid.")
