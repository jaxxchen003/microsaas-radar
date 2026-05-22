from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from analyzer import _candidate_priority, heuristic_analyze_post
from db import fetch_analyzed_posts, init_db, upsert_analyses, upsert_posts
from reporter import generate_csv_report, generate_html_report, generate_report_site
from scrapers.anysearch_scraper import _source_from_url, parse_anysearch_results
from scrapers.github_scraper import parse_github_issue_item
from scrapers.trustmrr_scraper import parse_trustmrr_startup
from signal_utils import extract_signal_matches, has_opportunity_signal


class SignalUtilsTest(unittest.TestCase):
    def test_detects_pain_and_relevance_keywords(self) -> None:
        pain, relevance = extract_signal_matches(
            "I wish there was a tool",
            "Doing this manually in my workflow is painful.",
        )
        self.assertIn("wish there was", pain)
        self.assertIn("doing this manually", pain)
        self.assertIn("tool", relevance)
        self.assertIn("workflow", relevance)
        self.assertTrue(has_opportunity_signal("I wish there was a tool", "manual workflow"))

    def test_rejects_missing_relevance(self) -> None:
        self.assertFalse(has_opportunity_signal("I wish there was something", ""))


class AnalyzerTest(unittest.TestCase):
    def test_heuristic_analysis_schema_and_score_bounds(self) -> None:
        analysis = heuristic_analyze_post(
            {
                "title": "I wish there was a tool for this workflow",
                "body": "I have to manually reconcile dashboards and would pay for automation.",
                "score": 120,
                "comments": 45,
                "pain_keywords": "wish there was, i have to manually, would pay for",
                "relevance_keywords": "tool, workflow, dashboard, automat",
            }
        )
        self.assertTrue(analysis["is_product_opportunity"])
        self.assertGreaterEqual(analysis["opportunity_score"], 1)
        self.assertLessEqual(analysis["opportunity_score"], 10)
        self.assertEqual(analysis["pay_signal"], "high")

    def test_candidate_priority_balances_source_and_engagement(self) -> None:
        anysearch_signal = {
            "source": "AnySearch/X/@founder",
            "score": 0,
            "comments": 0,
            "pain_keywords": "wish there was, would pay for",
            "relevance_keywords": "tool, workflow",
        }
        hn_signal = {
            "source": "HackerNews",
            "score": 200,
            "comments": 80,
            "pain_keywords": "wish there was",
            "relevance_keywords": "tool",
        }
        self.assertGreater(_candidate_priority(anysearch_signal), _candidate_priority(hn_signal))

    def test_trustmrr_signal_uses_market_validation_heuristic(self) -> None:
        analysis = heuristic_analyze_post(
            {
                "source": "TrustMRR/saas",
                "title": "Tiny CRM: verified revenue in saas",
                "mrr_cents": 25000,
                "last30_revenue_cents": 50000,
                "growth30d": 12,
                "category": "saas",
                "target_audience": "b2b",
            }
        )
        self.assertTrue(analysis["is_product_opportunity"])
        self.assertEqual(analysis["pay_signal"], "high")
        self.assertIn("verified revenue", analysis["pain_summary"].lower())


class DatabaseTest(unittest.TestCase):
    def test_upsert_and_fetch_analyzed_posts(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        init_db(connection)
        post = {
            "source": "Test",
            "title": "I wish there was a tool",
            "body": "manual workflow",
            "url": "https://example.com/1",
            "score": 5,
            "comments": 2,
            "pain_keywords": "wish there was",
            "relevance_keywords": "tool",
            "date": "2026-05-19",
        }
        self.assertEqual(upsert_posts(connection, [post, post]), 2)
        analyzed = {**post, **heuristic_analyze_post(post)}
        self.assertEqual(upsert_analyses(connection, [analyzed]), 1)
        rows = fetch_analyzed_posts(connection)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], post["url"])


class ReporterTest(unittest.TestCase):
    def test_generates_csv_and_escaped_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir)
            posts = [
                {
                    "source": "Test",
                    "title": '<script>alert("x")</script>',
                    "url": "https://example.com/?x=1&y=2",
                    "date": "2026-05-19",
                    "score": 10,
                    "comments": 5,
                    "pain_keywords": "wish there was",
                    "relevance_keywords": "tool",
                    "is_product_opportunity": True,
                    "pain_summary": "<b>pain</b>",
                    "current_workaround": None,
                    "target_user": "operators",
                    "product_idea": "automation",
                    "pay_signal": "medium",
                    "competition": "low",
                    "opportunity_score": 7,
                    "reason": "strong signal",
                }
            ]
            csv_path = generate_csv_report(posts, output / "opportunities.csv")
            html_path = generate_html_report(posts, output / "report.html")
            self.assertTrue(csv_path.exists())
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;", html_text)
            self.assertNotIn("<script>alert", html_text)
            self.assertIn("7/10", html_text)
            self.assertIn('data-lang="zh"', html_text)
            self.assertIn('data-theme="dark"', html_text)
            self.assertIn("Micro SaaS 需求雷达", html_text)
            self.assertIn("Micro SaaS Radar Report", html_text)
            self.assertIn('data-set-lang="en"', html_text)
            self.assertIn('data-filter="high-pay"', html_text)
            self.assertIn('data-score="7"', html_text)
            self.assertIn("痛点信号词", html_text)
            self.assertIn("Pay:", html_text)

    def test_generates_static_site_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            posts = [
                {
                    "source": "HN",
                    "title": "I wish there was a tool",
                    "url": "https://example.com/1",
                    "date": "2026-05-19",
                    "score": 10,
                    "comments": 5,
                    "pain_summary": "manual workflow",
                    "current_workaround": None,
                    "target_user": "operators",
                    "product_idea": "automation",
                    "pay_signal": "medium",
                    "competition": "low",
                    "opportunity_score": 7,
                    "reason": "strong signal",
                }
            ]
            paths = generate_report_site(posts, tmpdir, report_date="2026-05-19", min_score=7)
            self.assertTrue(paths["index_path"].exists())
            self.assertTrue(paths["latest_path"].exists())
            self.assertTrue(paths["report_path"].exists())
            self.assertTrue(paths["archive_path"].exists())
            self.assertEqual(paths["archive_path"].name, "2026-05-19.html")
            self.assertIn("Open latest report", paths["index_path"].read_text(encoding="utf-8"))
            self.assertIn("打开最新报告", paths["index_path"].read_text(encoding="utf-8"))
            latest_html = paths["latest_path"].read_text(encoding="utf-8")
            self.assertIn("High pay intent", latest_html)
            self.assertIn("高付费意愿", latest_html)
            self.assertIn('data-filter="score-8"', latest_html)


class AnySearchParserTest(unittest.TestCase):
    def test_parse_anysearch_markdown_results(self) -> None:
        markdown = """
## 搜索结果 (共 1 条，耗时 100ms)

### 1. I wish there was an AI tool that could - Reddit
- **链接**: https://www.reddit.com/r/SaaS/comments/example/i_wish/
- I wish there was a tool that could automate this workflow.
date: Aug 4, 2025
"""
        results = parse_anysearch_results(markdown)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://www.reddit.com/r/SaaS/comments/example/i_wish/")
        self.assertIn("automate this workflow", results[0]["snippet"])
        self.assertEqual(results[0]["date"], "Aug 4, 2025")

    def test_parse_anysearch_english_url_label(self) -> None:
        markdown = """
## Search Results (1 result, 100ms)

### 1. Does anyone else wish there was a simple dashboard? - Reddit
- **URL**: https://www.reddit.com/r/SaaS/comments/example/dashboard/
- I wish there was a simple tool for this workflow.
date: Feb 24, 2026
"""
        results = parse_anysearch_results(markdown)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://www.reddit.com/r/SaaS/comments/example/dashboard/")
        self.assertIn("simple tool", results[0]["snippet"])

    def test_anysearch_source_classification(self) -> None:
        self.assertEqual(
            _source_from_url("https://github.com/acme/tool/issues/1"),
            "AnySearch/GitHub/acme/tool",
        )
        self.assertEqual(
            _source_from_url("https://x.com/founder/status/1"),
            "AnySearch/X/@founder",
        )


class GitHubScraperTest(unittest.TestCase):
    def test_parse_github_issue_item(self) -> None:
        parsed = parse_github_issue_item(
            {
                "title": "I wish there was a tool for this workflow",
                "body": "We are doing this manually and need automation.",
                "html_url": "https://github.com/acme/tool/issues/1",
                "repository_url": "https://api.github.com/repos/acme/tool",
                "comments": 4,
                "updated_at": "2026-05-20T00:00:00Z",
                "labels": [{"name": "feature request"}],
                "reactions": {"+1": 3, "heart": 1, "rocket": 0, "eyes": 2},
            }
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["source"], "GitHub/acme/tool")
        self.assertEqual(parsed["score"], 10)
        self.assertIn("wish there was", parsed["pain_keywords"])
        self.assertIn("tool", parsed["relevance_keywords"])

    def test_parse_github_skips_pull_requests(self) -> None:
        self.assertIsNone(
            parse_github_issue_item(
                {
                    "title": "I wish there was a tool",
                    "body": "manual workflow",
                    "pull_request": {},
                }
            )
        )


class TrustMRRScraperTest(unittest.TestCase):
    def test_parse_trustmrr_startup(self) -> None:
        parsed = parse_trustmrr_startup(
            {
                "name": "WorkflowFox",
                "slug": "workflowfox",
                "description": "Automates small business workflows.",
                "category": "saas",
                "targetAudience": "b2b",
                "revenue": {"mrr": 12500, "last30Days": 22000, "total": 100000},
                "customers": 34,
                "activeSubscriptions": 12,
                "growth30d": 8,
                "growthMRR30d": 5,
                "foundedDate": "2026-01-01T00:00:00.000Z",
            }
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["source"], "TrustMRR/saas")
        self.assertEqual(parsed["url"], "https://trustmrr.com/startup/workflowfox")
        self.assertEqual(parsed["mrr_cents"], 12500)
        self.assertIn("verified revenue", parsed["pain_keywords"])


if __name__ == "__main__":
    unittest.main()
