from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from analyzer import heuristic_analyze_post
from db import fetch_analyzed_posts, init_db, upsert_analyses, upsert_posts
from reporter import generate_csv_report, generate_html_report, generate_report_site
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


if __name__ == "__main__":
    unittest.main()
