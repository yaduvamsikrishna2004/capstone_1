from __future__ import annotations

import logging

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from config import get_settings
from notifications.base import NotificationError, NotificationResult

logger = logging.getLogger(__name__)


def send_whatsapp_message(message: str) -> NotificationResult:
    settings = get_settings()

    required = {
        "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
        "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
        "TWILIO_WHATSAPP_NUMBER": settings.twilio_whatsapp_number,
        "YOUR_WHATSAPP_NUMBER": settings.your_whatsapp_number,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        error_message = f"Missing WhatsApp config: {', '.join(missing)}"
        logger.error(error_message)
        raise NotificationError(error_message)

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        response = client.messages.create(
            body=message,
            from_=settings.twilio_whatsapp_number,
            to=settings.your_whatsapp_number,
        )
        logger.info("WhatsApp message sent successfully. SID=%s", response.sid)
        return NotificationResult(
            success=True,
            channel="whatsapp",
            recipient=settings.your_whatsapp_number,
            provider_id=response.sid,
        )
    except TwilioRestException as error:
        logger.exception("Twilio WhatsApp API error: %s", error)
        raise NotificationError(str(error)) from error
    except Exception as error:
        logger.exception("Unexpected WhatsApp notification error: %s", error)
        raise NotificationError(str(error)) from error
