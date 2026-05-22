"""CLI entrypoint for Micro SaaS Radar."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

from analyzer import batch_analyze
from config import DEFAULT_DB_PATH, DEFAULT_OUTPUT_DIR
from db import connect, fetch_analyzed_posts, init_db, upsert_analyses, upsert_posts
from reporter import generate_csv_report, generate_report_site
from scrapers.anysearch_scraper import fetch_anysearch_opportunity_needs
from scrapers.gtrends import fetch_trend_topics
from scrapers.github_scraper import fetch_github_needs
from scrapers.hn_scraper import fetch_hn_needs
from scrapers.reddit_public_scraper import fetch_reddit_public_needs
from scrapers.reddit_scraper import fetch_reddit_needs
from scrapers.trustmrr_scraper import fetch_trustmrr_market_signals


async def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    print("=== Micro SaaS Radar started ===")
    output_dir = Path(args.output_dir)
    db_path = Path(args.db_path)

    with connect(db_path) as connection:
        init_db(connection)

        all_posts: list[dict[str, Any]] = []
        if not args.skip_hn:
            print("\n[1/4] Fetching HackerNews...")
            hn_posts = await fetch_hn_needs(limit_per_query=args.hn_limit)
            all_posts.extend(hn_posts)
            print(f"  HN: {len(hn_posts)} pain signals")

        if not args.skip_reddit:
            print("\n[2/4] Fetching Reddit...")
            reddit_posts = await fetch_reddit_needs(limit_per_sub=args.reddit_limit)
            if not reddit_posts and not args.skip_reddit_public:
                print("  OAuth returned no Reddit posts; trying public JSON fallback...")
                reddit_posts = await fetch_reddit_public_needs(
                    limit_per_sub=args.reddit_public_limit,
                    comments_per_post=args.reddit_comments,
                )
            all_posts.extend(reddit_posts)
            print(f"  Reddit: {len(reddit_posts)} pain signals")

        if not args.skip_github:
            print("\n[2.25/4] Searching GitHub issues...")
            github_posts = await fetch_github_needs(limit_per_query=args.github_limit)
            all_posts.extend(github_posts)
            print(f"  GitHub: {len(github_posts)} pain signals")

        if not args.skip_anysearch:
            print("\n[2.5/4] Searching indexed sources via AnySearch...")
            anysearch_posts = await fetch_anysearch_opportunity_needs(
                limit_per_query=args.anysearch_limit,
                freshness=args.anysearch_freshness,
            )
            all_posts.extend(anysearch_posts)
            print(f"  AnySearch: {len(anysearch_posts)} pain signals")

        if not args.skip_trustmrr:
            print("\n[2.75/4] Fetching TrustMRR market-validation signals...")
            trustmrr_posts = await fetch_trustmrr_market_signals(
                limit_per_category=args.trustmrr_limit,
            )
            all_posts.extend(trustmrr_posts)
            print(f"  TrustMRR: {len(trustmrr_posts)} market signals")

        if not args.skip_trends:
            print("\n[3/4] Fetching Google Trends enrichment...")
            trends = fetch_trend_topics()
            print(f"  Trends: {len(trends)} related rising queries")
        else:
            trends = []

        print(f"\n  Total scraped signals: {len(all_posts)}")
        stored_posts = upsert_posts(connection, all_posts)
        print(f"  Stored posts: {stored_posts}")

        print("\n[4/4] Analyzing and reporting...")
        analyzed = batch_analyze(
            all_posts,
            max_items=args.max_analyze,
            use_llm=not args.skip_llm,
            delay_seconds=args.analysis_delay,
        )
        stored_analyses = upsert_analyses(connection, analyzed)
        print(f"  Stored analyses: {stored_analyses}")

        report_rows = fetch_analyzed_posts(connection)
        csv_path = generate_csv_report(report_rows, output_dir / "opportunities.csv")
        site_paths = generate_report_site(
            report_rows,
            output_dir,
            report_date=args.report_date,
            min_score=args.min_score,
            history_limit=args.history_limit,
        )

    print("\nDone.")
    print(f"CSV: {csv_path}")
    print(f"Index: {site_paths['index_path']}")
    print(f"Latest: {site_paths['latest_path']}")
    print(f"Archive: {site_paths['archive_path']}")
    return {
        "posts": len(all_posts),
        "analyzed": len(analyzed),
        "trends": len(trends),
        "csv_path": str(csv_path),
        "index_path": str(site_paths["index_path"]),
        "latest_path": str(site_paths["latest_path"]),
        "archive_path": str(site_paths["archive_path"]),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover and score Micro SaaS opportunities.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Report output directory.")
    parser.add_argument("--hn-limit", type=int, default=30, help="HN hits per query.")
    parser.add_argument("--reddit-limit", type=int, default=100, help="Reddit posts per subreddit.")
    parser.add_argument("--reddit-public-limit", type=int, default=50, help="Public Reddit fallback posts per subreddit.")
    parser.add_argument("--reddit-comments", type=int, default=3, help="Top comments to include for public Reddit matches.")
    parser.add_argument("--github-limit", type=int, default=20, help="GitHub search results per query.")
    parser.add_argument("--anysearch-limit", type=int, default=8, help="AnySearch results per query.")
    parser.add_argument("--trustmrr-limit", type=int, default=5, help="TrustMRR results per category.")
    parser.add_argument(
        "--anysearch-freshness",
        default="year",
        choices=["day", "week", "month", "year"],
        help="AnySearch freshness window.",
    )
    parser.add_argument("--max-analyze", type=int, default=50, help="Max posts to analyze per run.")
    parser.add_argument("--analysis-delay", type=float, default=0.3, help="Delay between analysis calls.")
    parser.add_argument("--report-date", default=None, help="Report date in YYYY-MM-DD format.")
    parser.add_argument("--min-score", type=int, default=6, help="Minimum score shown in HTML reports.")
    parser.add_argument("--history-limit", type=int, default=30, help="Number of archived reports shown on index.")
    parser.add_argument("--skip-hn", action="store_true", help="Skip HackerNews scraping.")
    parser.add_argument("--skip-reddit", action="store_true", help="Skip Reddit scraping.")
    parser.add_argument("--skip-reddit-public", action="store_true", help="Skip public Reddit fallback.")
    parser.add_argument("--skip-github", action="store_true", help="Skip GitHub issue search.")
    parser.add_argument("--skip-anysearch", action="store_true", help="Skip AnySearch multi-source fallback.")
    parser.add_argument("--skip-trustmrr", action="store_true", help="Skip TrustMRR market-validation source.")
    parser.add_argument("--skip-trends", action="store_true", help="Skip Google Trends enrichment.")
    parser.add_argument("--skip-llm", action="store_true", help="Use heuristic analyzer only.")
    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    await run_pipeline(args)


if __name__ == "__main__":
    asyncio.run(main())
