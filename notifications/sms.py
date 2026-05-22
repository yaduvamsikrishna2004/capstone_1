from __future__ import annotations

import logging

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from config import get_settings
from notifications.base import NotificationError, NotificationResult

logger = logging.getLogger(__name__)


def send_sms(message: str) -> NotificationResult:
    settings = get_settings()

    required = {
        "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
        "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
        "TWILIO_SMS_NUMBER": settings.twilio_sms_number,
        "YOUR_PHONE_NUMBER": settings.your_phone_number,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        error_message = f"Missing SMS config: {', '.join(missing)}"
        logger.error(error_message)
        raise NotificationError(error_message)

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        response = client.messages.create(
            body=message,
            from_=settings.twilio_sms_number,
            to=settings.your_phone_number,
        )
        logger.info("SMS sent successfully. SID=%s", response.sid)
        return NotificationResult(
            success=True,
            channel="sms",
            recipient=settings.your_phone_number,
            provider_id=response.sid,
        )
    except TwilioRestException as error:
        logger.exception("Twilio SMS API error: %s", error)
        raise NotificationError(str(error)) from error
    except Exception as error:
        logger.exception("Unexpected SMS notification error: %s", error)
        raise NotificationError(str(error)) from error
