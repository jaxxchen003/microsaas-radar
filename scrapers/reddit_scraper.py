"""Reddit opportunity scraper using official OAuth client credentials."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUBREDDITS,
)
from signal_utils import extract_signal_matches

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"


async def fetch_reddit_needs(limit_per_sub: int = 100) -> list[dict[str, Any]]:
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        print("Reddit skipped: REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are not set.")
        return []

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": REDDIT_USER_AGENT}) as client:
        token = await _fetch_token(client)
        if not token:
            return []

        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": REDDIT_USER_AGENT,
        }
        for subreddit in SUBREDDITS:
            url = f"{API_BASE}/r/{subreddit}/new.json"
            params = {"limit": limit_per_sub}
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                print(f"Reddit error [r/{subreddit}]: {exc}")
                await asyncio.sleep(1)
                continue

            posts = data.get("data", {}).get("children", [])
            for item in posts:
                post = item.get("data", {})
                title = post.get("title", "")
                body = post.get("selftext", "")
                pain_matches, relevance_matches = extract_signal_matches(title, body)
                if not (pain_matches and relevance_matches):
                    continue
                results.append(
                    {
                        "source": f"Reddit/r/{subreddit}",
                        "title": title,
                        "body": body[:1000],
                        "url": "https://reddit.com" + post.get("permalink", ""),
                        "score": int(post.get("score") or 0),
                        "comments": int(post.get("num_comments") or 0),
                        "pain_keywords": ", ".join(pain_matches),
                        "relevance_keywords": ", ".join(relevance_matches),
                        "date": "",
                    }
                )
            await asyncio.sleep(1)
    return dedupe_by_url(results)


async def _fetch_token(client: httpx.AsyncClient) -> str:
    try:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
        )
        response.raise_for_status()
        return str(response.json().get("access_token") or "")
    except Exception as exc:
        print(f"Reddit OAuth error: {exc}")
        return ""


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
