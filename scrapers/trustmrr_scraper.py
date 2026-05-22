"""TrustMRR market-validation scraper."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from config import (
    TRUSTMRR_API_KEY,
    TRUSTMRR_CATEGORIES,
    TRUSTMRR_LIMIT_PER_CATEGORY,
    TRUSTMRR_MIN_MRR_CENTS,
)

TRUSTMRR_STARTUPS_URL = "https://trustmrr.com/api/v1/startups"


async def fetch_trustmrr_market_signals(
    limit_per_category: int = TRUSTMRR_LIMIT_PER_CATEGORY,
) -> list[dict[str, Any]]:
    """Fetch verified-revenue startup signals from TrustMRR.

    TrustMRR is not a raw pain source. It is a market-validation source for
    niches where small products already have verified revenue.
    """

    if not TRUSTMRR_API_KEY:
        print("TrustMRR skipped: TRUSTMRR_API_KEY is not set.")
        return []

    headers = {
        "Authorization": f"Bearer {TRUSTMRR_API_KEY}",
        "Accept": "application/json",
        "User-Agent": "microsaas-radar/1.0",
    }
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        for category in TRUSTMRR_CATEGORIES:
            params = {
                "category": category,
                "sort": "growth-desc",
                "limit": min(limit_per_category, 50),
                "minMrr": TRUSTMRR_MIN_MRR_CENTS,
            }
            try:
                response = await client.get(TRUSTMRR_STARTUPS_URL, params=params)
                if response.status_code == 401:
                    print("TrustMRR skipped: invalid TRUSTMRR_API_KEY.")
                    return results
                if response.status_code == 429:
                    await asyncio.sleep(int(response.headers.get("Retry-After", "5")))
                    response = await client.get(TRUSTMRR_STARTUPS_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                print(f"TrustMRR error [{category}]: {exc}")
                await asyncio.sleep(1)
                continue

            for item in payload.get("data", []):
                parsed = parse_trustmrr_startup(item)
                if parsed:
                    results.append(parsed)
            await asyncio.sleep(1)
    return _dedupe_by_url(results)


def parse_trustmrr_startup(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert TrustMRR startup data into a market-validation card input."""

    name = str(item.get("name") or "").strip()
    slug = str(item.get("slug") or "").strip()
    if not name or not slug:
        return None

    revenue = item.get("revenue") or {}
    mrr_cents = int(revenue.get("mrr") or 0)
    last30_cents = int(revenue.get("last30Days") or 0)
    growth = item.get("growth30d")
    growth_mrr = item.get("growthMRR30d")
    category = str(item.get("category") or "startup")
    target = str(item.get("targetAudience") or "unknown")
    description = str(item.get("description") or "").strip()
    website = str(item.get("website") or "")
    url = f"https://trustmrr.com/startup/{slug}"

    body_parts = [
        description,
        f"Verified revenue signal from TrustMRR: MRR ${mrr_cents / 100:.0f}, last 30 days revenue ${last30_cents / 100:.0f}.",
        f"Category: {category}. Target audience: {target}. Customers: {item.get('customers') or 0}. Active subscriptions: {item.get('activeSubscriptions') or 0}.",
    ]
    if growth is not None or growth_mrr is not None:
        body_parts.append(f"Growth: 30d revenue {growth}; MRR growth {growth_mrr}.")
    if website:
        body_parts.append(f"Website: {website}")

    return {
        "source": f"TrustMRR/{category}",
        "title": f"{name}: verified revenue in {category}",
        "body": "\n".join(part for part in body_parts if part)[:1600],
        "url": url,
        "score": _market_score(mrr_cents, last30_cents, growth, item.get("customers")),
        "comments": int(item.get("customers") or 0),
        "pain_keywords": "verified revenue, growth signal",
        "relevance_keywords": "saas, product, service, platform",
        "date": str(item.get("foundedDate") or "")[:10],
        "mrr_cents": mrr_cents,
        "last30_revenue_cents": last30_cents,
        "growth30d": growth,
        "category": category,
        "target_audience": target,
    }


def _market_score(
    mrr_cents: int,
    last30_cents: int,
    growth: object,
    customers: object,
) -> int:
    score = 0
    score += min(mrr_cents // 10000, 20)
    score += min(last30_cents // 10000, 20)
    try:
        score += min(int(float(growth or 0)), 20)
    except (TypeError, ValueError):
        pass
    try:
        score += min(int(customers or 0) // 10, 20)
    except (TypeError, ValueError):
        pass
    return int(score)


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
