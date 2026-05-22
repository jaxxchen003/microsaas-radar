"""GitHub issue search scraper for Micro SaaS pain signals."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import httpx

from config import GITHUB_SEARCH_QUERIES, GITHUB_TOKEN
from signal_utils import extract_signal_matches

GITHUB_SEARCH_URL = "https://api.github.com/search/issues"


async def fetch_github_needs(
    limit_per_query: int = 20,
    updated_within_days: int = 365,
) -> list[dict[str, Any]]:
    """Search public GitHub issues for repeated workflow complaints."""

    results: list[dict[str, Any]] = []
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "microsaas-radar/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    updated_after = (date.today() - timedelta(days=updated_within_days)).isoformat()
    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        for query in GITHUB_SEARCH_QUERIES:
            search_query = f"{query} updated:>={updated_after}"
            params = {
                "q": search_query,
                "sort": "updated",
                "order": "desc",
                "per_page": min(limit_per_query, 100),
            }
            try:
                response = await client.get(GITHUB_SEARCH_URL, params=params)
                if response.status_code == 403:
                    print("GitHub search skipped or rate-limited. Add GITHUB_TOKEN for higher limits.")
                    break
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                print(f"GitHub search error [{query}]: {exc}")
                await asyncio.sleep(1)
                continue

            for item in data.get("items", []):
                parsed = parse_github_issue_item(item)
                if parsed:
                    results.append(parsed)
            await asyncio.sleep(1)
    return _dedupe_by_url(results)


def parse_github_issue_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a GitHub Search API issue item into a pipeline post."""

    if "pull_request" in item:
        return None

    title = str(item.get("title") or "")
    body = str(item.get("body") or "")
    pain_matches, relevance_matches = extract_signal_matches(title, body)
    if not (pain_matches and relevance_matches):
        return None

    repo_url = str(item.get("repository_url") or "")
    repo_name = repo_url.rsplit("/repos/", 1)[-1] if "/repos/" in repo_url else ""
    labels = [
        label.get("name", "")
        for label in item.get("labels", [])
        if isinstance(label, dict) and label.get("name")
    ]
    reactions = item.get("reactions") or {}
    reaction_score = sum(
        int(reactions.get(key) or 0)
        for key in ("+1", "heart", "rocket", "eyes")
    )
    comments = int(item.get("comments") or 0)

    context = body[:1300]
    if labels:
        context = f"{context}\n\nLabels: {', '.join(labels)}"

    return {
        "source": f"GitHub/{repo_name}" if repo_name else "GitHub",
        "title": title,
        "body": context,
        "url": str(item.get("html_url") or ""),
        "score": reaction_score + comments,
        "comments": comments,
        "pain_keywords": ", ".join(pain_matches),
        "relevance_keywords": ", ".join(relevance_matches),
        "date": str(item.get("updated_at") or item.get("created_at") or "")[:10],
    }


def _dedupe_by_url(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for post in posts:
        url = str(post.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(post)
    return deduped
