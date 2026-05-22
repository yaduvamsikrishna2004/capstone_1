from __future__ import annotations

import logging

from utils import CHANNEL_LIMITS, fit_to_limit

logger = logging.getLogger(__name__)


def build_twitter_post(summary: str, hashtags: str = "#AI #RAG") -> str:
    """Create a Twitter/X-ready post under 280 characters."""
    limit = CHANNEL_LIMITS["twitter"]
    base = fit_to_limit(summary, max(limit - len(hashtags) - 1, 1))
    post = f"{base} {hashtags}".strip()
    return fit_to_limit(post, limit)


def send_twitter_post(summary: str) -> str:
    """
    Placeholder function for future Twitter/X API integration.

    Returns a post-ready string to keep the project beginner friendly without
    requiring additional API credentials right now.
    """
    post = build_twitter_post(summary)
    logger.info("Twitter post generated (preview mode).")
    return post
