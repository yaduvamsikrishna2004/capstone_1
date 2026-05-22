from __future__ import annotations

from dataclasses import dataclass


class NotificationError(RuntimeError):
    """Raised when a notification channel fails."""


@dataclass
class NotificationResult:
    success: bool
    channel: str
    recipient: str
    provider_id: str = ""
    error: str = ""
