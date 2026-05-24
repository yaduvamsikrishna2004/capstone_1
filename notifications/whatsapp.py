from __future__ import annotations

import logging
import re

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from config import get_settings
from notifications.base import NotificationError, NotificationResult

logger = logging.getLogger(__name__)


def _normalize_whatsapp_number(value: str) -> str:
    candidate = value.strip()
    if candidate.lower().startswith("whatsapp:"):
        candidate = candidate.split(":", 1)[1].strip()
    candidate = candidate.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if candidate and not candidate.startswith("+"):
        candidate = f"+{candidate}"
    if not re.fullmatch(r"^\+[1-9]\d{7,14}$", candidate):
        raise NotificationError(
            "WhatsApp number must be a valid phone number (example: +14155552671)."
        )
    return f"whatsapp:{candidate}"


def send_whatsapp_message(message: str, recipient: str | None = None) -> NotificationResult:
    settings = get_settings()
    raw_recipient = recipient or settings.your_whatsapp_number
    raw_sender = settings.twilio_whatsapp_number

    required = {
        "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
        "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
        "TWILIO_WHATSAPP_NUMBER": raw_sender,
        "YOUR_WHATSAPP_NUMBER": raw_recipient,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        error_message = f"Missing WhatsApp config: {', '.join(missing)}"
        logger.error(error_message)
        raise NotificationError(error_message)

    target_recipient = _normalize_whatsapp_number(raw_recipient)
    sender_number = _normalize_whatsapp_number(raw_sender)

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        response = client.messages.create(
            body=message,
            from_=sender_number,
            to=target_recipient,
        )
        logger.info("WhatsApp message sent successfully. SID=%s", response.sid)
        return NotificationResult(
            success=True,
            channel="whatsapp",
            recipient=target_recipient,
            provider_id=response.sid,
        )
    except TwilioRestException as error:
        logger.exception("Twilio WhatsApp API error: %s", error)
        raise NotificationError(str(error)) from error
    except Exception as error:
        logger.exception("Unexpected WhatsApp notification error: %s", error)
        raise NotificationError(str(error)) from error
