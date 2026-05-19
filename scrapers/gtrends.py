"""Optional Google Trends enrichment."""

from __future__ import annotations

from typing import Any

from config import TRENDS_KEYWORDS


def fetch_trend_topics(keywords: list[str] | None = None) -> list[dict[str, Any]]:
    try:
        from pytrends.request import TrendReq
    except Exception:
        print("Google Trends skipped: pytrends is not installed.")
        return []

    selected = keywords or TRENDS_KEYWORDS
    try:
        pytrends = TrendReq(hl="en-US", tz=360)
        pytrends.build_payload(selected, timeframe="today 3-m")
        related = pytrends.related_queries()
    except Exception as exc:
        print(f"Google Trends error: {exc}")
        return []

    topics: list[dict[str, Any]] = []
    for keyword, payload in related.items():
        rising = payload.get("rising")
        if rising is None:
            continue
        for row in rising.head(10).to_dict("records"):
            topics.append(
                {
                    "keyword": keyword,
                    "query": row.get("query", ""),
                    "value": row.get("value", 0),
                }
            )
    return topics
