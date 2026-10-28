# Architecture

Crypto News Radar is a static-first application. Collection runs in GitHub Actions; the browser reads a generated JSON file and does not need API credentials.

## Data flow

1. `config/sources.json` defines enabled RSS/Atom sources, language, topics, and source trust class.
2. `scripts/collect_news.py` fetches each feed independently, parses RSS or Atom XML, normalizes URLs and timestamps, assigns a stable ID, and merges duplicate links.
3. The collector writes `data/news.json` atomically. A failed feed is recorded in the source status list; successful feeds are still retained.
4. `scripts/validate_data.py` checks the source registry and generated event structure.
5. `.github/workflows/collect-news.yml` runs every two hours and commits changed generated data.
6. `.github/workflows/pages.yml` publishes the static dashboard to GitHub Pages.
7. `app.js` loads the JSON file and applies client-side search and filters.

## Event schema

Each event currently includes:

- `id`: stable SHA-256-derived identifier based on normalized URL.
- `title`, `url`: headline and original story link.
- `source_id`, `source_name`, `source_trust`: source metadata.
- `language`, `topics`: source language and configured topic labels.
- `published_at`: UTC timestamp when supplied by the feed, otherwise null.
- `summary`: optional feed-provided excerpt.
- `status`: currently `unreviewed`; it is not an assertion of truth.
- `collected_at`: collection timestamp.

## Reliability and trust

- Feed errors are isolated per source.
- Response size and request time are bounded.
- URLs must be HTTP(S) before they are stored.
- Unknown publication dates remain unknown.
- Feed trust labels describe source type, not the truth of every article.
- No private keys or API credentials are required for the RSS collector.

## Known first-release limitations

- Topic labels are configured per source, not yet classified per article.
- The dashboard uses browser-side search; there is no server or full-text index.
- Cross-publisher similarity detection is limited to normalized URL deduplication.
- English is the initial dominant language; source-level language metadata is supported.
- The collector depends on public feed availability and may be rate-limited or blocked by publishers.
