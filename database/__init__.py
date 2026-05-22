from __future__ import annotations

from config import get_settings
from database.manager import DatabaseError, DatabaseManager, SummaryRecord

_settings = get_settings()
_db_manager = DatabaseManager(_settings.sqlite_db_path)


def initialize_database() -> None:
    _db_manager.initialize()


def save_summary(query: str, summary: str, user_id: str | None = None, source_documents: str = "") -> None:
    active_user = user_id or _settings.default_user_id
    _db_manager.save_summary(
        user_id=active_user,
        query=query,
        summary=summary,
        source_documents=source_documents,
        model_name=_settings.ollama_model,
    )


def save_query_history(query: str, response: str, retrieved_count: int, user_id: str | None = None) -> None:
    active_user = user_id or _settings.default_user_id
    _db_manager.save_query_history(active_user, query, response, retrieved_count)


def save_notification_log(
    channel: str,
    recipient: str,
    status: str,
    message_preview: str,
    error_message: str = "",
    user_id: str | None = None,
) -> None:
    active_user = user_id or _settings.default_user_id
    _db_manager.save_notification_log(
        user_id=active_user,
        channel=channel,
        recipient=recipient,
        status=status,
        message_preview=message_preview,
        error_message=error_message,
    )


def view_summaries(limit: int = 20) -> list[tuple]:
    records = _db_manager.get_recent_summaries(limit=limit)
    return [
        (
            record.id,
            record.user_id,
            record.query,
            record.summary,
            record.source_documents,
            record.model_name,
            record.created_at,
        )
        for record in records
    ]


__all__ = [
    "DatabaseError",
    "DatabaseManager",
    "SummaryRecord",
    "initialize_database",
    "save_summary",
    "save_query_history",
    "save_notification_log",
    "view_summaries",
]
