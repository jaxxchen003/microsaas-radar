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

ANYSEARCH_REDDIT_QUERIES = [
    'site:reddit.com/r/SaaS "wish there was" tool',
    'site:reddit.com/r/Entrepreneur "would pay for" tool',
    'site:reddit.com/r/smallbusiness "doing this manually" software',
    'site:reddit.com/r/webdev "looking for a tool" workflow',
    'site:reddit.com/r/nocode "no good solution" automate',
]

ANYSEARCH_SOURCE_QUERIES = {
    "Reddit": ANYSEARCH_REDDIT_QUERIES,
    "X": [
        'site:x.com "wish there was" "tool"',
        'site:x.com "would pay for" "software"',
        'site:twitter.com "doing this manually" "workflow"',
        'site:twitter.com "looking for a tool" "automate"',
    ],
    "GitHub": [
        'site:github.com "wish there was" "tool" "issues"',
        'site:github.com "looking for a tool" "workflow" "issues"',
        'site:github.com "manual workflow" "automation" "issues"',
    ],
}

GITHUB_SEARCH_QUERIES = [
    '"wish there was" "tool" in:title,body type:issue',
    '"looking for a tool" "workflow" in:title,body type:issue',
    '"manual workflow" "automation" in:title,body type:issue',
    '"no good solution" "api" in:title,body type:issue',
    '"too expensive" "alternative" in:title,body type:issue',
]

TRUSTMRR_CATEGORIES = [
    "saas",
    "ai",
    "developer-tools",
    "productivity",
    "no-code",
    "analytics",
    "marketing",
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANYSEARCH_API_KEY = os.getenv("ANYSEARCH_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
TRUSTMRR_API_KEY = os.getenv("TRUSTMRR_API_KEY", "")
TRUSTMRR_MIN_MRR_CENTS = int(os.getenv("TRUSTMRR_MIN_MRR_CENTS", "1000"))
TRUSTMRR_LIMIT_PER_CATEGORY = int(os.getenv("TRUSTMRR_LIMIT_PER_CATEGORY", "5"))

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "microsaas-radar/1.0 (contact: local-dev)",
)
