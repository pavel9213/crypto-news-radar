# Crypto News Radar

<p>
  <a href="https://github.com/pavel9213/crypto-news-radar/actions/workflows/ci.yml"><img src="https://github.com/pavel9213/crypto-news-radar/actions/workflows/ci.yml/badge.svg" alt="CI status" /></a>
  <a href="https://github.com/pavel9213/crypto-news-radar/actions/workflows/collect-news.yml"><img src="https://github.com/pavel9213/crypto-news-radar/actions/workflows/collect-news.yml/badge.svg" alt="News collector status" /></a>
  <a href="https://github.com/pavel9213/crypto-news-radar/actions/workflows/pages.yml"><img src="https://github.com/pavel9213/crypto-news-radar/actions/workflows/pages.yml/badge.svg" alt="Dashboard deployment status" /></a>
  <a href="https://pavel9213.github.io/crypto-news-radar/"><img src="https://img.shields.io/badge/live-dashboard-visit-7C3AED?style=flat" alt="Live dashboard" /></a>
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fpavel9213%2Fcrypto-news-radar%2Fmain%2Fdata%2Fstatus.json" alt="Live stories and sources" />
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fpavel9213%2Fcrypto-news-radar%2Fmain%2Fdata%2Fupdated.json" alt="Last data refresh" />
</p>

A source-first news intelligence dashboard for cryptocurrency markets, blockchain/Web3, cryptography, cybersecurity, regulation, and research.

> **Project status:** Live dashboard with automated RSS/Atom collection, data validation, and scheduled updates. The project continues to expand source coverage and analysis.

## Goals

- Collect news from configured RSS and Atom feeds, including primary sources.
- Cover crypto markets, protocols, DeFi, Web3, token launches, cryptography, security incidents, regulation, and research.
- Normalize timestamps, URLs, categories, and source metadata.
- Deduplicate repeated stories while preserving source links.
- Distinguish confirmed primary-source announcements from reporting, unconfirmed claims, and rumors.
- Publish a searchable, filterable web interface backed by validated, generated data.
- Run tests and scheduled collection with GitHub Actions.

## Planned coverage

| Area | Example topics |
| --- | --- |
| Markets | BTC, ETH, altcoins, ETFs, exchanges, stablecoins, market structure |
| Blockchain & Web3 | L1/L2, DeFi, bridges, wallets, NFT, DAO, DePIN, airdrops, TGE |
| Cryptography | Encryption, signatures, zero-knowledge proofs, MPC, post-quantum cryptography |
| Security | Exploits, vulnerabilities, audits, wallet safety, incident response |
| Policy & institutions | Laws, regulators, court decisions, institutional adoption |
| Research & AI | Academic papers, protocol research, AI/crypto intersections |

Coverage will expand over time; no aggregator can guarantee every news item worldwide.

## Roadmap

### Phase 1 — Reliable data foundation
- Define a versioned event schema and source registry.
- Build a fault-tolerant RSS/Atom collector.
- Normalize and deduplicate events.
- Validate generated data and add unit tests.
- Keep source URL, publication time, fetch time, and confidence/status explicit.

### Phase 2 — Automated publishing
- Add scheduled and manually triggered GitHub Actions.
- Validate data before committing generated artifacts.
- Report source failures without discarding successful feeds.

### Phase 3 — Web dashboard
- Responsive news feed with search, date range, topic, source, language, and status filters.
- Event cards with original-source links and clear timestamps.
- Highlights for security incidents and major announcements.
- Accessible layout and useful empty/error states.

### Phase 4 — Intelligence features
- Cross-source story grouping.
- English/Russian coverage and language metadata.
- Importance ranking with transparent, rule-based signals.
- Optional summaries only when the original source remains visible.

## Data integrity principles

1. **Source first:** every item should link to its origin.
2. **No invented facts:** missing dates or details stay missing rather than being guessed.
3. **Evidence labels:** a report is not automatically an official confirmation.
4. **Rumors stay rumors:** never label speculation as confirmed.
5. **Resilient collection:** one broken feed must not stop all other feeds.
6. **Privacy and secrets:** credentials belong in GitHub Actions secrets, never in source files.
7. **Reproducibility:** validation and tests should run locally and in CI.

## Development

The collector and dashboard are implemented incrementally. Python's standard library is used where practical to keep CI simple and avoid unnecessary dependencies. Tests run in GitHub Actions.

## Contributing

Please report source problems, incorrect categorization, duplicates, or missing coverage through GitHub Issues. Include the original URL and explain what should be corrected.

## Disclaimer

This project is an informational news aggregator, not financial, investment, legal, or security advice. Classification is automated and can be wrong; verify consequential claims against primary sources.
