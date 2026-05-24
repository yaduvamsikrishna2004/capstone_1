from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
from rag import RAGError, get_rag_service
from sms import NotificationError as SMSNotificationError
from sms import send_sms
from utils import fit_to_limit, setup_logging
from whatsapp import NotificationError as WhatsAppNotificationError
from whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    user_id: str = Field(default="web_user", min_length=1, max_length=120)


class DeliveryRequest(BaseModel):
    destination: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    user_id: str = Field(default="web_user", min_length=1, max_length=120)
    subject: str = Field(default="AI Generated Summary", max_length=200)


settings = get_settings()
setup_logging(log_level="INFO", log_file=settings.project_root / "logs" / "api.log")
initialize_database()
rag_service = get_rag_service()

app = FastAPI(title="DocAI Assistant API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_txt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _read_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())


def _ingest_path(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        report = rag_service.ingest_pdf(path)
    elif suffix == ".txt":
        report = rag_service.ingest_text_document(source_name=path.name, text=_read_txt(path))
    elif suffix == ".docx":
        report = rag_service.ingest_text_document(source_name=path.name, text=_read_docx(path))
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    return {
        "file": path.name,
        "chunks_created": report.chunks_created,
        "chunks_indexed": report.chunks_indexed,
        "chunks_skipped": report.chunks_skipped,
    }


def _normalize_phone_number(value: str) -> str:
    candidate = value.strip()
    if candidate.lower().startswith("whatsapp:"):
        candidate = candidate.split(":", 1)[1].strip()
    candidate = candidate.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if candidate and not candidate.startswith("+"):
        candidate = f"+{candidate}"
    if not PHONE_REGEX.fullmatch(candidate):
        raise HTTPException(
            status_code=422,
            detail="Phone number must be in E.164 format (example: +14155552671).",
        )
    return candidate


def _validate_email_address(value: str) -> str:
    candidate = value.strip()
    if not EMAIL_REGEX.fullmatch(candidate):
        raise HTTPException(status_code=422, detail="Recipient email format is invalid.")
    return candidate


def _channel_config_ready() -> dict[str, Any]:
    email_ready = bool(settings.email_address and settings.email_app_password and settings.receiver_email)
    whatsapp_ready = bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_whatsapp_number
        and settings.your_whatsapp_number
    )
    sms_ready = bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_sms_number
        and settings.your_phone_number
    )
    return {
        "email": {"configured": email_ready},
        "whatsapp": {"configured": whatsapp_ready},
        "sms": {"configured": sms_ready},
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/notification-health")
def notification_health() -> dict[str, Any]:
    channels = _channel_config_ready()
    ready = all(item["configured"] for item in channels.values())
    return {"status": "ok" if ready else "partial", "channels": channels}


@app.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    saved_paths: list[Path] = []
    for upload in files:
        if not upload.filename:
            continue
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt"}:
            raise HTTPException(status_code=400, detail=f"Unsupported file type for {upload.filename}")

        target_path = settings.documents_dir / Path(upload.filename).name
        content = await upload.read()
        target_path.write_bytes(content)
        saved_paths.append(target_path)

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid files were uploaded.")

    reports: list[dict[str, Any]] = []
    total_chunks_created = 0
    total_chunks_indexed = 0
    total_chunks_skipped = 0

    try:
        for path in saved_paths:
            file_report = _ingest_path(path)
            reports.append(file_report)
            total_chunks_created += int(file_report["chunks_created"])
            total_chunks_indexed += int(file_report["chunks_indexed"])
            total_chunks_skipped += int(file_report["chunks_skipped"])
    except (RAGError, ValueError) as error:
        logger.exception("Upload ingestion failed: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "status": "success",
        "files_processed": len(reports),
        "chunks_created": total_chunks_created,
        "chunks_indexed": total_chunks_indexed,
        "chunks_skipped": total_chunks_skipped,
        "files": reports,
    }


@app.post("/ask")
def ask_question(payload: AskRequest) -> dict[str, Any]:
    try:
        rag_response = rag_service.answer_query(payload.question, user_id=payload.user_id)

        source_list = sorted({f"{chunk.source}:p{chunk.page}" for chunk in rag_response.chunks})
        source_text = ", ".join(source_list)
        save_summary(
            query=payload.question,
            summary=rag_response.answer,
            source_documents=source_text,
            user_id=payload.user_id,
        )
        save_query_history(
            query=payload.question,
            response=rag_response.answer,
            retrieved_count=len(rag_response.chunks),
            user_id=payload.user_id,
        )

        return {
            "answer": rag_response.answer,
            "sources": [
                {
                    "source": chunk.source,
                    "page": chunk.page,
                    "score": chunk.score,
                }
                for chunk in rag_response.chunks
            ],
            "retrieved_count": len(rag_response.chunks),
        }
    except (RAGError, DatabaseError, ValueError) as error:
        logger.exception("Failed to answer question: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/history")
def get_history(limit: int = 20) -> dict[str, Any]:
    try:
        rows = view_summaries(limit=limit)
    except DatabaseError as error:
        logger.exception("Failed to fetch history: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error

    records = [
        {
            "id": row[0],
            "user_id": row[1],
            "query": row[2],
            "summary": row[3],
            "source_documents": row[4],
            "model_name": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]
    return {"items": records}


@app.post("/send-email")
def send_email_endpoint(payload: DeliveryRequest) -> dict[str, Any]:
    destination = _validate_email_address(payload.destination)
    logger.info("Notification request received: channel=email destination=%s user_id=%s", destination, payload.user_id)
    try:
        result = send_email(body=payload.message, subject=payload.subject, recipient=destination)
        save_notification_log(
            channel="email",
            recipient=result.recipient,
            status="success",
            message_preview=fit_to_limit(payload.message, 120),
            user_id=payload.user_id,
        )
        return {
            "status": "sent",
            "channel": "email",
            "recipient": result.recipient,
            "provider_id": result.provider_id,
        }
    except (EmailNotificationError, Exception) as error:
        save_notification_log(
            channel="email",
            recipient=destination,
            status="failed",
            message_preview=fit_to_limit(payload.message, 120),
            error_message=str(error),
            user_id=payload.user_id,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/send-whatsapp")
def send_whatsapp_endpoint(payload: DeliveryRequest) -> dict[str, Any]:
    destination = _normalize_phone_number(payload.destination)
    logger.info("Notification request received: channel=whatsapp destination=%s user_id=%s", destination, payload.user_id)
    try:
        result = send_whatsapp_message(message=payload.message, recipient=destination)
        save_notification_log(
            channel="whatsapp",
            recipient=result.recipient,
            status="success",
            message_preview=fit_to_limit(payload.message, 120),
            user_id=payload.user_id,
        )
        return {
            "status": "sent",
            "channel": "whatsapp",
            "recipient": result.recipient,
            "provider_id": result.provider_id,
        }
    except (WhatsAppNotificationError, Exception) as error:
        save_notification_log(
            channel="whatsapp",
            recipient=destination,
            status="failed",
            message_preview=fit_to_limit(payload.message, 120),
            error_message=str(error),
            user_id=payload.user_id,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/send-sms")
def send_sms_endpoint(payload: DeliveryRequest) -> dict[str, Any]:
    destination = _normalize_phone_number(payload.destination)
    logger.info("Notification request received: channel=sms destination=%s user_id=%s", destination, payload.user_id)
    try:
        result = send_sms(message=payload.message, recipient=destination)
        save_notification_log(
            channel="sms",
            recipient=result.recipient,
            status="success",
            message_preview=fit_to_limit(payload.message, 120),
            user_id=payload.user_id,
        )
        return {
            "status": "sent",
            "channel": "sms",
            "recipient": result.recipient,
            "provider_id": result.provider_id,
        }
    except (SMSNotificationError, Exception) as error:
        save_notification_log(
            channel="sms",
            recipient=destination,
            status="failed",
            message_preview=fit_to_limit(payload.message, 120),
            error_message=str(error),
            user_id=payload.user_id,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error
