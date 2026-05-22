"""Reddit opportunity scraper using the public JSON endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from config import REDDIT_USER_AGENT, SUBREDDITS
from signal_utils import extract_signal_matches

REDDIT_BASE = "https://www.reddit.com"
MAX_COMMENT_CONCURRENCY = 2


async def fetch_reddit_public_needs(
    limit_per_sub: int = 50,
    comments_per_post: int = 3,
) -> list[dict[str, Any]]:
    """Fetch Reddit posts without OAuth.

    This is a best-effort fallback inspired by Horizon's public JSON scraper.
    It keeps concurrency low to reduce rate-limit pressure and enriches matching
    posts with a few high-signal comments.
    """

    results: list[dict[str, Any]] = []
    headers = {
        "User-Agent": REDDIT_USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    comment_sem = asyncio.Semaphore(MAX_COMMENT_CONCURRENCY)

    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        for subreddit in SUBREDDITS:
            url = f"{REDDIT_BASE}/r/{subreddit}/new.json"
            params = {"limit": min(limit_per_sub, 100), "raw_json": 1}
            try:
                response = await client.get(url, params=params)
                if response.status_code == 429:
                    await asyncio.sleep(int(response.headers.get("Retry-After", "5")))
                    response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                print(f"Reddit public error [r/{subreddit}]: {exc}")
                await asyncio.sleep(1)
                continue

            posts = [
                child.get("data", {})
                for child in data.get("data", {}).get("children", [])
                if child.get("kind") == "t3"
            ]
            for post in posts:
                title = post.get("title", "")
                body = post.get("selftext", "")
                pain_matches, relevance_matches = extract_signal_matches(title, body)
                if not (pain_matches and relevance_matches):
                    continue

                comments = await _fetch_top_comments(
                    client,
                    comment_sem,
                    post.get("subreddit", subreddit),
                    post.get("id", ""),
                    comments_per_post,
                )
                comment_block = _format_comments(comments)
                full_body = body
                if comment_block:
                    full_body = f"{body[:1000]}\n\n--- Top Comments ---\n{comment_block}"

                results.append(
                    {
                        "source": f"RedditPublic/r/{subreddit}",
                        "title": title,
                        "body": full_body[:1800],
                        "url": "https://reddit.com" + post.get("permalink", ""),
                        "score": int(post.get("score") or 0),
                        "comments": int(post.get("num_comments") or 0),
                        "pain_keywords": ", ".join(pain_matches),
                        "relevance_keywords": ", ".join(relevance_matches),
                        "date": _date_from_utc(post.get("created_utc")),
                    }
                )
            await asyncio.sleep(1)
    return _dedupe_by_url(results)


async def _fetch_top_comments(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    subreddit: str,
    post_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    if not post_id or limit <= 0:
        return []
    url = f"{REDDIT_BASE}/r/{subreddit}/comments/{post_id}.json"
    params = {"limit": limit, "depth": 1, "sort": "top", "raw_json": 1}
    try:
        async with semaphore:
            response = await client.get(url, params=params)
        if response.status_code in (403, 404, 429):
            return []
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []
    if not isinstance(data, list) or len(data) < 2:
        return []

    comments: list[dict[str, Any]] = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        comment = child.get("data", {})
        if comment.get("distinguished") == "moderator":
            continue
        if comment.get("body"):
            comments.append(comment)
    comments.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    return comments[:limit]


def _format_comments(comments: list[dict[str, Any]]) -> str:
    lines = []
    for comment in comments:
        body = " ".join(str(comment.get("body") or "").split())
        if not body:
            continue
        lines.append(f"[{comment.get('author', 'anon')} | {int(comment.get('score') or 0)} pts] {body[:350]}")
    return "\n".join(lines)


def _date_from_utc(value: object) -> str:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return ""


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
