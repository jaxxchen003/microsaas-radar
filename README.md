# Micro SaaS Radar

Micro SaaS Radar finds public pain signals from HackerNews and Reddit, scores them with OpenAI or a local heuristic fallback, stores them in SQLite, and exports CSV plus HTML reports.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional credentials:

```bash
export OPENAI_API_KEY="..."
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USER_AGENT="microsaas-radar/1.0 (by /u/yourusername)"
```

## Run

```bash
python main.py
```

No-key smoke run:

```bash
python main.py --skip-reddit --skip-trends --skip-llm --max-analyze 5
```

Outputs:

- `needs.db`
- `output/opportunities.csv`
- `output/index.html`
- `output/latest.html`
- `output/report.html`
- `output/reports/YYYY-MM-DD.html`

## Scheduling

### Local cron

```cron
0 9 * * * cd /path/to/microsaas-radar && . .venv/bin/activate && python main.py
```

### GitHub Actions

The repository includes `.github/workflows/daily-report.yml`. It runs every day at 09:00 Asia/Shanghai and can also be started manually from the Actions tab.

Optional repository secrets:

- `OPENAI_API_KEY`: enables OpenAI scoring. Without it, the heuristic analyzer is used.
- `REDDIT_CLIENT_ID`: enables Reddit scraping.
- `REDDIT_CLIENT_SECRET`: enables Reddit scraping.
- `REDDIT_USER_AGENT`: recommended for Reddit API requests.

The workflow commits these generated files back to the repository:

- `output/opportunities.csv`
- `output/index.html`
- `output/latest.html`
- `output/report.html`
- `output/reports/YYYY-MM-DD.html`

The stable daily viewing entrypoint is `output/latest.html`. `output/index.html` keeps the lightweight static-site archive.
HTML pages default to Chinese UI copy and include Chinese/English language switching, dark/light theme switching, top metrics, filter chips, and scan-friendly opportunity tags.

## Source Notes

- HackerNews uses the public Algolia Search API.
- Reddit uses the official OAuth client credentials flow.
- Google Trends is best-effort via `pytrends` and may be rate-limited by the upstream service.
- X/Twitter and G2 are intentionally left as future source modules because they need separate API access and compliance review.
