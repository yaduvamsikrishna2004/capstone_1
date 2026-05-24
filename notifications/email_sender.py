from __future__ import annotations

import logging
import re
import smtplib
import socket
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import get_settings
from notifications.base import NotificationError, NotificationResult

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 20
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _build_message(sender: str, receiver: str, subject: str, body: str) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def send_email(body: str, subject: str = "AI Generated Summary", recipient: str | None = None) -> NotificationResult:
    settings = get_settings()
    target_recipient = (recipient or settings.receiver_email).strip()

    required = {
        "EMAIL_ADDRESS": settings.email_address,
        "EMAIL_APP_PASSWORD or EMAIL_PASSWORD": settings.email_app_password,
        "RECEIVER_EMAIL": target_recipient,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        error_message = f"Missing email config: {', '.join(missing)}"
        logger.error(error_message)
        raise NotificationError(error_message)

    if not EMAIL_REGEX.fullmatch(target_recipient):
        raise NotificationError("Recipient email address format is invalid.")

    msg = _build_message(settings.email_address, target_recipient, subject, body)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(settings.email_address, settings.email_app_password)
                server.send_message(msg)

            logger.info("Email sent successfully to %s", target_recipient)
            return NotificationResult(
                success=True,
                channel="email",
                recipient=target_recipient,
                provider_id="smtp",
            )

        except smtplib.SMTPAuthenticationError as error:
            logger.exception("Gmail SMTP authentication failed: %s", error)
            raise NotificationError(
                "Gmail authentication failed. Use a valid Google App Password for EMAIL_ADDRESS."
            ) from error
        except (
            smtplib.SMTPConnectError,
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPHeloError,
            smtplib.SMTPDataError,
            TimeoutError,
            socket.gaierror,
        ) as error:
            logger.exception("Transient SMTP error on attempt %s/%s: %s", attempt, MAX_RETRIES, error)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            raise NotificationError(f"SMTP connection failure after retries: {error}") from error
        except smtplib.SMTPException as error:
            logger.exception("SMTP failure: %s", error)
            raise NotificationError(str(error)) from error
        except Exception as error:
            logger.exception("Unexpected email notification error: %s", error)
            raise NotificationError(str(error)) from error

    raise NotificationError("Email send failed after retries.")


def send_test_email() -> NotificationResult:
    return send_email(
        body=(
            "This is a test email from capstone_rag. "
            "If you received this, Gmail App Password auth works."
        ),
        subject="capstone_rag SMTP Test",
    )
