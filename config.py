"""Runtime configuration for Micro SaaS Radar."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "needs.db"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"

PAIN_SIGNAL_KEYWORDS = [
    "wish there was",
    "why is there no",
    "can't find a tool",
    "doing this manually",
    "frustrated with",
    "workaround for",
    "i wish there was",
    "no good solution",
    "would pay for",
    "willing to pay",
    "looking for a tool that",
    "is there a way to automate",
    "i have to manually",
    "does anyone know a tool",
    "hate that i have to",
]

RELEVANCE_KEYWORDS = [
    "tool",
    "saas",
    "app",
    "software",
    "automat",
    "workflow",
    "api",
    "startup",
    "product",
    "service",
    "platform",
    "bot",
    "script",
    "integration",
    "dashboard",
    "plugin",
    "ai",
]

SUBREDDITS = [
    "microsaas",
    "indiehackers",
    "SaaS",
    "entrepreneur",
    "smallbusiness",
    "nocode",
    "webdev",
    "freelance",
]

HN_QUERIES = [
    "Ask HN: Is there a tool",
    "Ask HN: Why is there no",
    "Ask HN: I wish there was",
    "micro saas",
    "saas pain point",
    "automate workflow",
]

TRENDS_KEYWORDS = [
    "micro saas",
    "workflow automation",
    "no code automation",
    "ai productivity tool",
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "microsaas-radar/1.0 (contact: local-dev)",
)
