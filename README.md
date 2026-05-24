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
export ANYSEARCH_API_KEY="..."
export GITHUB_TOKEN="..."
export TRUSTMRR_API_KEY="..."
```

`ANYSEARCH_API_KEY` is optional. Anonymous AnySearch access is used with lower limits when the key is not set.
`GITHUB_TOKEN` is optional but increases GitHub Search API limits. `TRUSTMRR_API_KEY` is optional and enables verified-revenue market-validation cards from the official TrustMRR API.

## Run

```bash
python main.py
```

No-key smoke run:

```bash
python main.py --skip-reddit --skip-trends --skip-llm --skip-trustmrr --max-analyze 5
```

Outputs:

- `needs.db`
- `output/opportunities.csv`
- `output/index.html`
- `output/latest.html`
- `output/report.html`
- `output/reports/YYYY-MM-DD.html`

## Public Report

GitHub Pages publishes the generated `output/` directory after every successful daily workflow run:

https://jaxxchen003.github.io/microsaas-radar/

## Scheduling

### Local cron

```cron
0 9 * * * cd /path/to/microsaas-radar && . .venv/bin/activate && python main.py
```

### GitHub Actions

The repository includes `.github/workflows/daily-report.yml`. It tries several morning schedules between 07:37 and 12:37 Asia/Shanghai because GitHub can delay or skip scheduled workflow starts. Scheduled runs skip automatically when the current day's archived report already exists. The workflow can also be started manually from the Actions tab.

Optional repository secrets:

- `OPENAI_API_KEY`: enables OpenAI scoring. Without it, the heuristic analyzer is used.
- `REDDIT_CLIENT_ID`: enables Reddit scraping.
- `REDDIT_CLIENT_SECRET`: enables Reddit scraping.
- `REDDIT_USER_AGENT`: recommended for Reddit API requests.
- `ANYSEARCH_API_KEY`: optional higher-limit AnySearch key for Reddit, X/Twitter, and GitHub indexed search fallback.
- `GITHUB_TOKEN`: optional higher-limit GitHub Search API token.
- `TRUSTMRR_API_KEY`: optional TrustMRR API key for verified revenue and market-validation signals.

The workflow commits these generated files back to the repository:

- `output/opportunities.csv`
- `output/index.html`
- `output/latest.html`
- `output/report.html`
- `output/reports/YYYY-MM-DD.html`

It also deploys the same `output/` directory to GitHub Pages, so the public report URL stays stable while the content updates daily.

The stable daily viewing entrypoint is `output/latest.html`. `output/index.html` keeps the lightweight static-site archive.
HTML pages default to Chinese UI copy and include Chinese/English language switching, dark/light theme switching, top metrics, filter chips, and scan-friendly opportunity tags.

## Source Notes

- HackerNews uses the public Algolia Search API.
- Reddit uses the official OAuth client credentials flow when configured, then falls back to Reddit public JSON endpoints with top-comment context.
- GitHub searches public issues for workflow complaints, feature requests, manual workarounds, and expensive-alternative signals.
- AnySearch searches indexed Reddit, X/Twitter, and GitHub pages as a no-secret fallback.
- TrustMRR uses the official API as an optional market-validation source for verified MRR, last-30-day revenue, growth, customer count, and categories. It is treated differently from pain posts: it validates a niche rather than proving a user complaint.
- Google Trends is best-effort via `pytrends` and may be rate-limited by the upstream service.
- X/Twitter direct scraping remains a future module because stable direct access needs separate API access and compliance review; current support is best-effort through AnySearch indexed pages.
