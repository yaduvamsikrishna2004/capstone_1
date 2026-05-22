from __future__ import annotations

import logging
from pathlib import Path

from config import get_settings
from database import (
    DatabaseError,
    initialize_database,
    save_notification_log,
    save_query_history,
    save_summary,
    view_summaries,
)
from email_sender import NotificationError as EmailNotificationError
from email_sender import send_email
from rag import RAGError, generate_short_summary, get_rag_service, ingest_pdfs
from sms import send_sms
from utils import fit_to_limit, setup_logging
from whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)


def _read_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Input cannot be empty. Try again.")


def _yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    value = input(f"{prompt} {suffix}: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def _choose_pdfs(documents_dir: Path) -> list[Path]:
    pdf_files = sorted(documents_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in {documents_dir}. Add one or more PDFs and try again."
        )

    print("\nAvailable PDFs:")
    for index, path in enumerate(pdf_files, start=1):
        print(f"{index}. {path.name}")

    choice = input("Select file numbers (comma-separated) or type 'all': ").strip().lower()
    if choice == "all":
        return pdf_files

    selected: list[Path] = []
    for token in choice.split(","):
        token = token.strip()
        if not token.isdigit():
            continue
        idx = int(token)
        if 1 <= idx <= len(pdf_files):
            selected.append(pdf_files[idx - 1])

    if not selected:
        raise ValueError("No valid PDF selection made.")

    return selected


def _send_notifications(user_id: str, full_answer: str) -> None:
    if not _yes_no("Send notifications?", default=False):
        return

    if _yes_no("Send WhatsApp?", default=True):
        msg = generate_short_summary(full_answer, channel="whatsapp")
        try:
            result = send_whatsapp_message(msg)
            save_notification_log(
                channel="whatsapp",
                recipient=result.recipient,
                status="success",
                message_preview=fit_to_limit(msg, 120),
                user_id=user_id,
            )
            print(f"WhatsApp sent (SID: {result.provider_id})")
        except Exception as error:
            save_notification_log(
                channel="whatsapp",
                recipient="unknown",
                status="failed",
                message_preview=fit_to_limit(msg, 120),
                error_message=str(error),
                user_id=user_id,
            )
            print(f"WhatsApp failed: {error}")

    if _yes_no("Send SMS?", default=True):
        msg = generate_short_summary(full_answer, channel="sms")
        try:
            result = send_sms(msg)
            save_notification_log(
                channel="sms",
                recipient=result.recipient,
                status="success",
                message_preview=fit_to_limit(msg, 120),
                user_id=user_id,
            )
            print(f"SMS sent (SID: {result.provider_id})")
        except Exception as error:
            save_notification_log(
                channel="sms",
                recipient="unknown",
                status="failed",
                message_preview=fit_to_limit(msg, 120),
                error_message=str(error),
                user_id=user_id,
            )
            print(f"SMS failed: {error}")

    if _yes_no("Send Email?", default=False):
        msg = generate_short_summary(full_answer, channel="whatsapp")
        try:
            result = send_email(full_answer)
            save_notification_log(
                channel="email",
                recipient=result.recipient,
                status="success",
                message_preview=fit_to_limit(msg, 120),
                user_id=user_id,
            )
            print("Email sent.")
        except (EmailNotificationError, Exception) as error:
            save_notification_log(
                channel="email",
                recipient="unknown",
                status="failed",
                message_preview=fit_to_limit(msg, 120),
                error_message=str(error),
                user_id=user_id,
            )
            print(f"Email failed: {error}")


def _ingest_menu(settings_path: Path) -> None:
    selected = _choose_pdfs(settings_path)
    report = ingest_pdfs(selected)
    print(
        "Ingestion complete: "
        f"files={report.files_processed}, chunks={report.chunks_created}, "
        f"new={report.chunks_indexed}, skipped_duplicates={report.chunks_skipped}"
    )


def _ask_menu(user_id: str) -> None:
    query = _read_non_empty("\nAsk a question: ")

    rag_service = get_rag_service()
    rag_response = rag_service.answer_query(query, user_id=user_id)

    print("\nAI RESPONSE:\n")
    print(rag_response.answer)

    source_list = sorted({f"{c.source}:p{c.page}" for c in rag_response.chunks})
    source_text = ", ".join(source_list)

    save_summary(
        query=query,
        summary=rag_response.answer,
        source_documents=source_text,
        user_id=user_id,
    )
    save_query_history(
        query=query,
        response=rag_response.answer,
        retrieved_count=len(rag_response.chunks),
        user_id=user_id,
    )

    _send_notifications(user_id=user_id, full_answer=rag_response.answer)


def _history_menu() -> None:
    rows = view_summaries(limit=10)
    if not rows:
        print("No summaries saved yet.")
        return

    print("\nRecent Summaries:")
    for row in rows:
        print(row)


def main() -> None:
    settings = get_settings()
    setup_logging(log_level="INFO", log_file=settings.project_root / "logs" / "app.log")

    print("Capstone RAG Assistant")
    user_id = input("Enter user id (optional): ").strip() or settings.default_user_id

    try:
        initialize_database()
    except DatabaseError as error:
        logger.error("Failed to initialize database: %s", error)
        print(f"Database initialization failed: {error}")
        return

    while True:
        print("\nMenu")
        print("1. Ingest PDF(s)")
        print("2. Ask a question")
        print("3. View recent summaries")
        print("4. Exit")

        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                _ingest_menu(settings.documents_dir)
            elif choice == "2":
                _ask_menu(user_id=user_id)
            elif choice == "3":
                _history_menu()
            elif choice == "4":
                print("Goodbye.")
                break
            else:
                print("Invalid option. Please choose 1-4.")
        except (FileNotFoundError, ValueError, RAGError, DatabaseError) as error:
            logger.exception("Operation failed: %s", error)
            print(f"Error: {error}")
        except Exception as error:
            logger.exception("Unexpected application error: %s", error)
            print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()
