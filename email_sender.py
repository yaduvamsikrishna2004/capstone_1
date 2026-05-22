import logging
import os
import socket
import ssl
import smtplib
import time
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 20
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2


def _load_env() -> None:
    """Load .env variables once per process."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        logger.warning(".env file not found at expected path: %s", env_path)
    load_dotenv(dotenv_path=env_path, override=False)


def _is_value_missing(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip() == ""


def _validate_env_vars() -> tuple[str, str, str]:
    email_address = os.getenv("EMAIL_ADDRESS")
    # Prefer dedicated app-password variable if present.
    email_password = os.getenv("EMAIL_APP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL")

    missing_vars: list[str] = []

    if _is_value_missing(email_address):
        missing_vars.append("EMAIL_ADDRESS")
    if _is_value_missing(email_password):
        missing_vars.append("EMAIL_APP_PASSWORD or EMAIL_PASSWORD")
    if _is_value_missing(receiver_email):
        missing_vars.append("RECEIVER_EMAIL")

    if missing_vars:
        logger.error("Missing required email env vars: %s", ", ".join(missing_vars))
        raise ValueError(
            "Missing required email configuration. "
            "Set EMAIL_ADDRESS, EMAIL_APP_PASSWORD (or EMAIL_PASSWORD), and RECEIVER_EMAIL in .env."
        )

    # ValueError path guarantees non-None values below.
    normalized_email = email_address.strip()
    normalized_receiver = receiver_email.strip()

    # Google App Passwords are 16 characters and are often shown in 4-char groups.
    # Removing whitespace prevents copy/paste formatting issues.
    normalized_password = "".join(email_password.split())
    normalized_password = normalized_password.strip("\"'")

    if len(normalized_password) < 16:
        logger.warning(
            "EMAIL_PASSWORD looks shorter than expected after whitespace cleanup "
            "(length=%s). Verify Google App Password copy/paste.",
            len(normalized_password),
        )

    logger.info(
        "Email config loaded: EMAIL_ADDRESS set=%s, RECEIVER_EMAIL set=%s, APP_PASSWORD length=%s",
        bool(normalized_email),
        bool(normalized_receiver),
        len(normalized_password),
    )

    return normalized_email, normalized_password, normalized_receiver


def _build_message(sender: str, receiver: str, subject: str, body: str) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def send_email(summary: str, subject: str = "AI Generated Summary") -> bool:
    """
    Send an email through Gmail SMTP using App Password auth.

    Returns True on success, False on failure.
    """
    _load_env()

    try:
        email_address, email_password, receiver_email = _validate_env_vars()
    except ValueError as error:
        logger.exception("Email configuration validation failed: %s", error)
        return False

    msg = _build_message(email_address, receiver_email, subject, summary)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(email_address, email_password)
                server.send_message(msg)

            print("Email sent successfully.")
            return True

        except smtplib.SMTPAuthenticationError as error:
            logger.exception(
                "Gmail authentication failed on attempt %s/%s. "
                "Use a Google App Password (not your normal Gmail password).",
                attempt,
                MAX_RETRIES,
            )
            logger.error("SMTP error details: %s", error)
            logger.error(
                "Auth checklist: 2-Step Verification enabled, App Password generated "
                "from the same Gmail account as EMAIL_ADDRESS, and no revoked app password."
            )
            return False

        except (
            smtplib.SMTPConnectError,
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPHeloError,
            smtplib.SMTPDataError,
            TimeoutError,
            socket.gaierror,
        ) as error:
            logger.exception(
                "Transient SMTP/network error on attempt %s/%s: %s",
                attempt,
                MAX_RETRIES,
                error,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            return False

        except smtplib.SMTPException as error:
            logger.exception("SMTP failure while sending email: %s", error)
            return False

        except Exception as error:
            logger.exception("Unexpected email error: %s", error)
            return False

    return False


def send_test_email() -> bool:
    """Send a short test email to verify configuration."""
    test_body = (
        "This is a Gmail SMTP test email from capstone_rag.\n\n"
        "If you received this message, EMAIL_ADDRESS/EMAIL_PASSWORD/RECEIVER_EMAIL are configured correctly."
    )
    return send_email(test_body, subject="capstone_rag SMTP Test")
