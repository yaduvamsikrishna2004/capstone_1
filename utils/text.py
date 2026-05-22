from __future__ import annotations

import re

CHANNEL_LIMITS = {
    "whatsapp": 800,
    "sms": 280,
    "twitter": 280,
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fit_to_limit(text: str, limit: int) -> str:
    clean_text = normalize_whitespace(text)
    if len(clean_text) <= limit:
        return clean_text

    if limit <= 3:
        return clean_text[:limit]

    return clean_text[: limit - 3].rstrip() + "..."
