from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Raised when an SQLite operation fails."""


@dataclass
class SummaryRecord:
    id: int
    user_id: str
    query: str
    summary: str
    source_documents: str
    model_name: str
    created_at: str


class DatabaseManager:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    def _add_column_if_missing(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_sql: str,
    ) -> None:
        columns = self._table_columns(conn, table_name)
        if column_name in columns:
            return

        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
        logger.info("Migrated table '%s': added column '%s'.", table_name, column_name)

    def _migrate_summaries_schema(self, conn: sqlite3.Connection) -> None:
        # Backward-compatible migration for old DBs that only had (id, query, summary).
        self._add_column_if_missing(
            conn,
            table_name="summaries",
            column_name="user_id",
            column_sql="user_id TEXT NOT NULL DEFAULT 'default_user'",
        )
        self._add_column_if_missing(
            conn,
            table_name="summaries",
            column_name="source_documents",
            column_sql="source_documents TEXT DEFAULT ''",
        )
        self._add_column_if_missing(
            conn,
            table_name="summaries",
            column_name="model_name",
            column_sql="model_name TEXT DEFAULT ''",
        )
        self._add_column_if_missing(
            conn,
            table_name="summaries",
            column_name="created_at",
            column_sql="created_at TEXT NOT NULL DEFAULT ''",
        )

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as error:
            logger.exception("SQLite operation failed: %s", error)
            raise DatabaseError(str(error)) from error
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def initialize(self) -> None:
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_documents TEXT DEFAULT '',
                    model_name TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            self._migrate_summaries_schema(conn)

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    retrieved_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message_preview TEXT NOT NULL,
                    error_message TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )

        logger.info("Database initialized at %s", self.db_path)

    def save_summary(
        self,
        user_id: str,
        query: str,
        summary: str,
        source_documents: str,
        model_name: str,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO summaries (user_id, query, summary, source_documents, model_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, query, summary, source_documents, model_name, created_at),
            )

        logger.info("Summary saved for user_id=%s", user_id)

    def save_query_history(self, user_id: str, query: str, response: str, retrieved_count: int) -> None:
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO query_history (user_id, query, response, retrieved_count, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, query, response, retrieved_count, created_at),
            )

    def save_notification_log(
        self,
        user_id: str,
        channel: str,
        recipient: str,
        status: str,
        message_preview: str,
        error_message: str = "",
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO notification_logs (user_id, channel, recipient, status, message_preview, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, channel, recipient, status, message_preview, error_message, created_at),
            )

    def get_recent_summaries(self, limit: int = 20) -> list[SummaryRecord]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, query, summary, source_documents, model_name, created_at
                FROM summaries
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            SummaryRecord(
                id=row["id"],
                user_id=row["user_id"],
                query=row["query"],
                summary=row["summary"],
                source_documents=row["source_documents"],
                model_name=row["model_name"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
