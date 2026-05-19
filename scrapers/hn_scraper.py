"""HackerNews opportunity scraper using the Algolia API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from config import HN_QUERIES
from signal_utils import extract_signal_matches

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


async def fetch_hn_needs(limit_per_query: int = 30) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15) as client:
        for query in HN_QUERIES:
            params = {"query": query, "tags": "story", "hitsPerPage": limit_per_query}
            try:
                response = await client.get(HN_SEARCH_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                print(f"HN error [{query}]: {exc}")
                await asyncio.sleep(0.5)
                continue

            for hit in data.get("hits", []):
                title = hit.get("title") or hit.get("story_title") or ""
                body = hit.get("story_text") or ""
                pain_matches, relevance_matches = extract_signal_matches(title, body)
                if not (pain_matches and relevance_matches):
                    continue

                object_id = hit.get("objectID", "")
                results.append(
                    {
                        "source": "HackerNews",
                        "title": title,
                        "body": body[:1000],
                        "url": hit.get("url")
                        or f"https://news.ycombinator.com/item?id={object_id}",
                        "score": int(hit.get("points") or 0),
                        "comments": int(hit.get("num_comments") or 0),
                        "pain_keywords": ", ".join(pain_matches),
                        "relevance_keywords": ", ".join(relevance_matches),
                        "date": (hit.get("created_at") or "")[:10],
                    }
                )
            await asyncio.sleep(0.5)
    return dedupe_by_url(results)


def dedupe_by_url(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for post in posts:
        url = str(post.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(post)
    return deduped
