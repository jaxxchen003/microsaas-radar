"""SQLite persistence for Micro SaaS Radar."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from config import DEFAULT_DB_PATH


POST_COLUMNS = [
    "source",
    "title",
    "body",
    "url",
    "score",
    "comments",
    "pain_keywords",
    "relevance_keywords",
    "date",
]


ANALYSIS_COLUMNS = [
    "is_product_opportunity",
    "pain_summary",
    "current_workaround",
    "target_user",
    "product_idea",
    "pay_signal",
    "competition",
    "opportunity_score",
    "reason",
]


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL UNIQUE,
            score INTEGER NOT NULL DEFAULT 0,
            comments INTEGER NOT NULL DEFAULT 0,
            pain_keywords TEXT NOT NULL DEFAULT '',
            relevance_keywords TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            post_url TEXT PRIMARY KEY,
            is_product_opportunity INTEGER NOT NULL DEFAULT 0,
            pain_summary TEXT NOT NULL DEFAULT '',
            current_workaround TEXT,
            target_user TEXT NOT NULL DEFAULT '',
            product_idea TEXT NOT NULL DEFAULT '',
            pay_signal TEXT NOT NULL DEFAULT 'low',
            competition TEXT NOT NULL DEFAULT 'medium',
            opportunity_score INTEGER NOT NULL DEFAULT 1,
            reason TEXT NOT NULL DEFAULT '',
            analyzed_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_url) REFERENCES posts(url)
        )
        """
    )
    connection.commit()


def upsert_posts(connection: sqlite3.Connection, posts: list[dict[str, Any]]) -> int:
    count = 0
    for post in posts:
        url = str(post.get("url") or "").strip()
        title = str(post.get("title") or "").strip()
        if not url or not title:
            continue
        values = {column: post.get(column, "") for column in POST_COLUMNS}
        values["score"] = int(values.get("score") or 0)
        values["comments"] = int(values.get("comments") or 0)
        connection.execute(
            """
            INSERT INTO posts (
                source, title, body, url, score, comments, pain_keywords,
                relevance_keywords, date, raw_json
            )
            VALUES (
                :source, :title, :body, :url, :score, :comments, :pain_keywords,
                :relevance_keywords, :date, :raw_json
            )
            ON CONFLICT(url) DO UPDATE SET
                source = excluded.source,
                title = excluded.title,
                body = excluded.body,
                score = excluded.score,
                comments = excluded.comments,
                pain_keywords = excluded.pain_keywords,
                relevance_keywords = excluded.relevance_keywords,
                date = excluded.date,
                raw_json = excluded.raw_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            {**values, "raw_json": json.dumps(post, ensure_ascii=False)},
        )
        count += 1
    connection.commit()
    return count


def upsert_analyses(connection: sqlite3.Connection, analyzed_posts: list[dict[str, Any]]) -> int:
    count = 0
    for post in analyzed_posts:
        url = str(post.get("url") or "").strip()
        if not url:
            continue
        values = {column: post.get(column) for column in ANALYSIS_COLUMNS}
        values["post_url"] = url
        values["is_product_opportunity"] = 1 if post.get("is_product_opportunity") else 0
        values["opportunity_score"] = int(post.get("opportunity_score") or 1)
        connection.execute(
            """
            INSERT INTO analyses (
                post_url, is_product_opportunity, pain_summary, current_workaround,
                target_user, product_idea, pay_signal, competition,
                opportunity_score, reason, analyzed_json
            )
            VALUES (
                :post_url, :is_product_opportunity, :pain_summary, :current_workaround,
                :target_user, :product_idea, :pay_signal, :competition,
                :opportunity_score, :reason, :analyzed_json
            )
            ON CONFLICT(post_url) DO UPDATE SET
                is_product_opportunity = excluded.is_product_opportunity,
                pain_summary = excluded.pain_summary,
                current_workaround = excluded.current_workaround,
                target_user = excluded.target_user,
                product_idea = excluded.product_idea,
                pay_signal = excluded.pay_signal,
                competition = excluded.competition,
                opportunity_score = excluded.opportunity_score,
                reason = excluded.reason,
                analyzed_json = excluded.analyzed_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            {**values, "analyzed_json": json.dumps(post, ensure_ascii=False)},
        )
        count += 1
    connection.commit()
    return count


def fetch_analyzed_posts(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT
            p.source, p.title, p.body, p.url, p.score, p.comments,
            p.pain_keywords, p.relevance_keywords, p.date,
            a.is_product_opportunity, a.pain_summary, a.current_workaround,
            a.target_user, a.product_idea, a.pay_signal, a.competition,
            a.opportunity_score, a.reason
        FROM posts p
        JOIN analyses a ON a.post_url = p.url
        ORDER BY a.opportunity_score DESC, p.score DESC
        """
    )
    rows = []
    for row in cursor.fetchall():
        record = dict(row)
        record["is_product_opportunity"] = bool(record["is_product_opportunity"])
        rows.append(record)
    return rows
