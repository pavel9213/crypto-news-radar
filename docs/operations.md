# Operations guide

## Run locally

Requires Python 3.10 or newer. No third-party Python packages are required.

```bash
python -m unittest discover -s tests -v
python scripts/validate_data.py
python scripts/collect_news.py
python scripts/validate_data.py
```

The collector writes `data/news.json`. Network access is required only for collection.

## Run collection manually

1. Open the repository's **Actions** tab.
2. Select **Collect crypto news**.
3. Choose **Run workflow** on the main branch.
4. Open the run and inspect the per-source logs.
5. If all feeds fail, check connectivity, feed URL changes, and publisher rate limits.

A single source failure is expected to be non-fatal. If every configured source fails, the collector exits unsuccessfully so the problem is visible in Actions.

## Enable GitHub Pages

1. Open **Settings → Pages** in the repository.
2. Set the build and deployment source to **GitHub Actions**.
3. Ensure Actions are permitted to write Pages deployments (the workflow declares the required permissions).
4. Run **Deploy dashboard** from Actions, or push a change to the dashboard files.
5. Once deployment succeeds, use the URL shown in the workflow's `github-pages` environment.

The dashboard reads `data/news.json` from the deployed site. If no collection has completed, a valid empty JSON file is used so the interface can still deploy.

## Troubleshooting

- **No stories:** run the collection workflow and inspect the source-level logs.
- **One source fails:** confirm the publisher still serves RSS/Atom and that the URL returns XML.
- **Dashboard deploy fails:** verify Pages is set to GitHub Actions and inspect the deploy job permissions.
- **Tests fail:** run the exact unittest command above and fix the first failing assertion before publishing.
- **Unexpected story classification:** the initial release only uses source-level topics; article-level classification is planned.

## Safety

Do not commit access tokens, API keys, cookies, or personal credentials. If optional authenticated providers are added later, store credentials in repository Actions secrets and document the exact permissions required.
