"""Reddit discovery via AnySearch, used when Reddit OAuth credentials are absent."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from config import ANYSEARCH_API_KEY, ANYSEARCH_REDDIT_QUERIES, ANYSEARCH_SOURCE_QUERIES
from signal_utils import extract_signal_matches

ANYSEARCH_ENDPOINT = "https://api.anysearch.com/mcp"


async def fetch_anysearch_reddit_needs(
    limit_per_query: int = 8,
    freshness: str = "year",
) -> list[dict[str, Any]]:
    """Search indexed Reddit pages through AnySearch.

    AnySearch supports anonymous access with lower limits. This path is not a
    replacement for Reddit OAuth; it is a no-secret fallback that can keep the
    daily report populated with Reddit-origin signals.
    """

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for query in ANYSEARCH_REDDIT_QUERIES:
            try:
                markdown = await _search(client, query, limit_per_query, freshness)
            except Exception as exc:
                print(f"AnySearch Reddit error [{query}]: {exc}")
                await asyncio.sleep(0.5)
                continue

            for item in parse_anysearch_results(markdown):
                title = item.get("title", "")
                body = item.get("snippet", "")
                url = item.get("url", "")
                if "reddit.com/" not in url:
                    continue
                pain_matches, relevance_matches = extract_signal_matches(title, body)
                if not (pain_matches and relevance_matches):
                    continue
                results.append(
                    {
                        "source": _source_from_reddit_url(url),
                        "title": title,
                        "body": body[:1000],
                        "url": url,
                        "score": 0,
                        "comments": 0,
                        "pain_keywords": ", ".join(pain_matches),
                        "relevance_keywords": ", ".join(relevance_matches),
                        "date": item.get("date", ""),
                    }
                )
            await asyncio.sleep(0.5)
    return dedupe_by_url(results)


async def fetch_anysearch_opportunity_needs(
    limit_per_query: int = 8,
    freshness: str = "year",
) -> list[dict[str, Any]]:
    """Search multiple indexed surfaces through AnySearch.

    This keeps X/Twitter and GitHub as no-secret, best-effort sources. Results
    still pass through the local pain/relevance signal gate before LLM scoring.
    """

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for source_family, queries in ANYSEARCH_SOURCE_QUERIES.items():
            for query in queries:
                try:
                    markdown = await _search(client, query, limit_per_query, freshness)
                except Exception as exc:
                    print(f"AnySearch {source_family} error [{query}]: {exc}")
                    await asyncio.sleep(0.5)
                    continue

                for item in parse_anysearch_results(markdown):
                    title = item.get("title", "")
                    body = item.get("snippet", "")
                    url = item.get("url", "")
                    if not _is_supported_url(url):
                        continue
                    pain_matches, relevance_matches = extract_signal_matches(title, body)
                    if not (pain_matches and relevance_matches):
                        continue
                    results.append(
                        {
                            "source": _source_from_url(url, default=f"AnySearch/{source_family}"),
                            "title": title,
                            "body": body[:1000],
                            "url": url,
                            "score": 0,
                            "comments": 0,
                            "pain_keywords": ", ".join(pain_matches),
                            "relevance_keywords": ", ".join(relevance_matches),
                            "date": item.get("date", ""),
                        }
                    )
                await asyncio.sleep(0.5)
    return dedupe_by_url(results)


async def _search(
    client: httpx.AsyncClient,
    query: str,
    limit_per_query: int,
    freshness: str,
) -> str:
    headers = {"Content-Type": "application/json"}
    if ANYSEARCH_API_KEY:
        headers["Authorization"] = f"Bearer {ANYSEARCH_API_KEY}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search",
            "arguments": {
                "query": query,
                "max_results": limit_per_query,
                "freshness": freshness,
            },
        },
    }
    response = await client.post(ANYSEARCH_ENDPOINT, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    for item in data.get("result", {}).get("content", []):
        if item.get("type") == "text":
            return str(item.get("text") or "")
    return ""


def parse_anysearch_results(markdown: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    snippet_parts: list[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        title_match = re.match(r"^###\s+\d+\.\s+(.*)$", line)
        if title_match:
            if current:
                current["snippet"] = " ".join(snippet_parts).strip()
                items.append(current)
            current = {"title": title_match.group(1).strip(), "url": "", "date": "", "snippet": ""}
            snippet_parts = []
            continue
        if not current:
            continue
        link_match = re.match(r"^-\s+\*\*(?:链接|URL|Link)\*\*:\s+(\S+)", line, flags=re.IGNORECASE)
        if link_match:
            current["url"] = link_match.group(1).strip()
            continue
        date_match = re.match(r"^date:\s+(.+)$", line, flags=re.IGNORECASE)
        if date_match:
            current["date"] = date_match.group(1).strip()
            continue
        if line.startswith("- "):
            snippet_parts.append(line[2:].strip())

    if current:
        current["snippet"] = " ".join(snippet_parts).strip()
        items.append(current)
    return items


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


def _source_from_reddit_url(url: str) -> str:
    match = re.search(r"reddit\.com/r/([^/]+)", url, flags=re.IGNORECASE)
    if not match:
        return "AnySearch/Reddit"
    return f"AnySearch/Reddit/r/{match.group(1)}"


def _is_supported_url(url: str) -> bool:
    normalized = url.lower()
    return any(
        domain in normalized
        for domain in ("reddit.com/", "x.com/", "twitter.com/", "github.com/")
    )


def _source_from_url(url: str, default: str = "AnySearch") -> str:
    normalized = url.lower()
    if "reddit.com/" in normalized:
        return _source_from_reddit_url(url)
    if "github.com/" in normalized:
        match = re.search(r"github\.com/([^/\s]+/[^/\s]+)", url, flags=re.IGNORECASE)
        return f"AnySearch/GitHub/{match.group(1)}" if match else "AnySearch/GitHub"
    if "x.com/" in normalized or "twitter.com/" in normalized:
        match = re.search(r"(?:x|twitter)\.com/([^/\s?]+)", url, flags=re.IGNORECASE)
        return f"AnySearch/X/@{match.group(1)}" if match else "AnySearch/X"
    return default
