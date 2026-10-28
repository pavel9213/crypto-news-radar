# Crypto News Radar

A source-first news intelligence dashboard for cryptocurrency markets, blockchain/Web3, cryptography, cybersecurity, regulation, and research.

> **Project status:** Foundation phase. The roadmap is intentionally staged: first build a reliable collector and validated data pipeline, then ship the dashboard, then expand coverage and analysis.

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

The project is being built incrementally. The initial implementation will use Python's standard library where practical to keep CI simple and avoid unnecessary dependencies. See the documentation and tests as they are added.

## Contributing

Please report source problems, incorrect categorization, duplicates, or missing coverage through GitHub Issues. Include the original URL and explain what should be corrected.

## Disclaimer

This project is an informational news aggregator, not financial, investment, legal, or security advice. Classification is automated and can be wrong; verify consequential claims against primary sources.
