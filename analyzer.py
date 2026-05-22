"""LLM and fallback analysis for opportunity posts."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from config import OPENAI_API_KEY, OPENAI_MODEL

ANALYSIS_PROMPT = """
你是一个Micro SaaS产品机会分析专家。分析以下帖子，判断是否存在可商业化的产品机会。

帖子标题：{title}
帖子内容：{body}
来源：{source}

注意：如果来源是 TrustMRR，这不是用户抱怨帖，而是已验证收入的市场验证信号。请判断它能否帮助验证某个 Micro SaaS 赛道，产品方向应聚焦“可借鉴的细分市场/目标用户/差异化机会”，不要把它误判成用户原帖。

请返回如下JSON格式（不要包含markdown代码块）：
{{
  "is_product_opportunity": true/false,
  "pain_summary": "用一句话概括核心痛点",
  "current_workaround": "用户现在如何解决这个问题（没有则填null）",
  "target_user": "谁会有这个痛点（职业/场景）",
  "product_idea": "可能的Micro SaaS产品形态（1-2句话）",
  "pay_signal": "high/medium/low（用户付费意愿）",
  "competition": "high/medium/low（竞争激烈程度）",
  "opportunity_score": 1-10（综合产品机会分，10分最高）,
  "reason": "评分理由（1-2句话）"
}}
"""

REQUIRED_ANALYSIS_KEYS = {
    "is_product_opportunity",
    "pain_summary",
    "current_workaround",
    "target_user",
    "product_idea",
    "pay_signal",
    "competition",
    "opportunity_score",
    "reason",
}


def analyze_post(post: dict[str, Any], use_llm: bool = True) -> dict[str, Any]:
    if _is_trustmrr_signal(post):
        return heuristic_analyze_post(post)
    if use_llm and OPENAI_API_KEY:
        analysis = _analyze_with_openai(post)
        if analysis:
            return normalize_analysis(analysis)
    return heuristic_analyze_post(post)


def _analyze_with_openai(post: dict[str, Any]) -> dict[str, Any]:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = ANALYSIS_PROMPT.format(
            title=post.get("title", ""),
            body=str(post.get("body", ""))[:800],
            source=post.get("source", ""),
        )
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        content = response.choices[0].message.content or ""
        return _parse_json_object(content)
    except Exception as exc:
        print(f"LLM error: {exc}")
        return {}


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


def heuristic_analyze_post(post: dict[str, Any]) -> dict[str, Any]:
    if _is_trustmrr_signal(post):
        return _heuristic_trustmrr_analysis(post)

    title = str(post.get("title") or "").strip()
    body = str(post.get("body") or "").strip()
    pain_keywords = _split_keywords(post.get("pain_keywords", ""))
    relevance_keywords = _split_keywords(post.get("relevance_keywords", ""))
    score = int(post.get("score") or 0)
    comments = int(post.get("comments") or 0)

    opportunity_score = 4
    opportunity_score += min(len(pain_keywords), 3)
    opportunity_score += min(len(relevance_keywords), 2)
    if score >= 50:
        opportunity_score += 1
    if comments >= 20:
        opportunity_score += 1
    if "pay" in " ".join(pain_keywords).lower() or "pay" in (title + body).lower():
        opportunity_score += 1
    opportunity_score = max(1, min(10, opportunity_score))

    text = body or title
    pain_summary = _first_sentence(text) or "用户表达了现有工具或流程无法满足需求。"
    pay_signal = "high" if "pay" in (title + body).lower() else "medium"

    return {
        "is_product_opportunity": opportunity_score >= 6,
        "pain_summary": pain_summary,
        "current_workaround": "manual workflow" if "manual" in (title + body).lower() else None,
        "target_user": "Builders, operators, or teams facing this workflow",
        "product_idea": "Build a focused automation or workflow tool around the repeated pain signal.",
        "pay_signal": pay_signal,
        "competition": "medium",
        "opportunity_score": opportunity_score,
        "reason": "Heuristic score based on pain keywords, relevance keywords, post score, and comment activity.",
    }


def _heuristic_trustmrr_analysis(post: dict[str, Any]) -> dict[str, Any]:
    title = str(post.get("title") or "").strip()
    body = str(post.get("body") or "").strip()
    category = str(post.get("category") or "micro saas")
    target = str(post.get("target_audience") or "founders or operators")
    mrr_cents = int(post.get("mrr_cents") or 0)
    last30_cents = int(post.get("last30_revenue_cents") or 0)
    score = 5
    if mrr_cents >= 100000:
        score += 2
    elif mrr_cents >= 10000:
        score += 1
    if last30_cents >= 100000:
        score += 1
    if post.get("growth30d") not in (None, "", 0):
        score += 1
    score = max(1, min(10, score))
    return {
        "is_product_opportunity": score >= 6,
        "pain_summary": (
            f"TrustMRR shows verified revenue in the {category} niche: "
            f"MRR ${mrr_cents / 100:.0f}, last-30-day revenue ${last30_cents / 100:.0f}."
        ),
        "current_workaround": None,
        "target_user": target,
        "product_idea": (
            f"Use this as market-validation evidence for a focused {category} product; "
            "look for underserved workflows around the same buyer and distribution channel."
        ),
        "pay_signal": "high" if mrr_cents >= 10000 or last30_cents >= 10000 else "medium",
        "competition": "high" if mrr_cents >= 100000 else "medium",
        "opportunity_score": score,
        "reason": (
            "Heuristic TrustMRR score based on verified MRR, recent revenue, and growth fields. "
            f"Signal: {title or body[:80]}"
        ),
    }


def normalize_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(analysis)
    normalized.setdefault("is_product_opportunity", False)
    normalized.setdefault("pain_summary", "")
    normalized.setdefault("current_workaround", None)
    normalized.setdefault("target_user", "")
    normalized.setdefault("product_idea", "")
    normalized.setdefault("pay_signal", "low")
    normalized.setdefault("competition", "medium")
    normalized.setdefault("opportunity_score", 1)
    normalized.setdefault("reason", "")

    try:
        normalized["opportunity_score"] = int(normalized["opportunity_score"])
    except (TypeError, ValueError):
        normalized["opportunity_score"] = 1
    normalized["opportunity_score"] = max(1, min(10, normalized["opportunity_score"]))
    normalized["pay_signal"] = _normalize_level(normalized.get("pay_signal"), "low")
    normalized["competition"] = _normalize_level(normalized.get("competition"), "medium")
    normalized["is_product_opportunity"] = bool(normalized.get("is_product_opportunity"))
    return {key: normalized[key] for key in REQUIRED_ANALYSIS_KEYS}


def batch_analyze(
    posts: list[dict[str, Any]],
    max_items: int = 50,
    use_llm: bool = True,
    delay_seconds: float = 0.3,
) -> list[dict[str, Any]]:
    top_posts = sorted(posts, key=lambda item: int(item.get("score") or 0), reverse=True)[:max_items]
    analyzed: list[dict[str, Any]] = []
    for index, post in enumerate(top_posts):
        print(f"  Analyzing {index + 1}/{len(top_posts)}: {str(post.get('title', ''))[:60]}...")
        analysis = analyze_post(post, use_llm=use_llm)
        merged = {**post, **analysis}
        analyzed.append(merged)
        if delay_seconds > 0:
            time.sleep(delay_seconds)
    return analyzed


def _split_keywords(value: object) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _first_sentence(text: str) -> str:
    clean = " ".join(text.split())
    if not clean:
        return ""
    parts = re.split(r"(?<=[.!?。！？])\s+", clean)
    return parts[0][:180]


def _normalize_level(value: object, default: str) -> str:
    value_text = str(value or "").lower()
    if "high" in value_text:
        return "high"
    if "medium" in value_text:
        return "medium"
    if "low" in value_text:
        return "low"
    return default


def _is_trustmrr_signal(post: dict[str, Any]) -> bool:
    return str(post.get("source") or "").lower().startswith("trustmrr/")
