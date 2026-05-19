"""Shared text matching helpers."""

from __future__ import annotations

from config import PAIN_SIGNAL_KEYWORDS, RELEVANCE_KEYWORDS


def normalize_text(*parts: object) -> str:
    return " ".join(str(part or "") for part in parts).lower()


def find_keyword_matches(text: str, keywords: list[str]) -> list[str]:
    normalized = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in normalized]


def extract_signal_matches(title: str, body: str) -> tuple[list[str], list[str]]:
    text = normalize_text(title, body)
    pain_matches = find_keyword_matches(text, PAIN_SIGNAL_KEYWORDS)
    relevance_matches = find_keyword_matches(text, RELEVANCE_KEYWORDS)
    return pain_matches, relevance_matches


def has_opportunity_signal(title: str, body: str) -> bool:
    pain_matches, relevance_matches = extract_signal_matches(title, body)
    return bool(pain_matches and relevance_matches)
