from __future__ import annotations

from pathlib import Path
from typing import Any

from config import get_settings
from rag.pipeline import IngestionReport, RAGError, RAGResponse, RAGService, RetrievedChunk

_settings = get_settings()
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(_settings)
    return _rag_service


def list_pdf_files() -> list[Path]:
    return get_rag_service().list_available_pdfs()


def ingest_pdfs(file_paths: list[str | Path]) -> IngestionReport:
    return get_rag_service().ingest_documents(file_paths)


def load_pdf(file_path: str | Path) -> list[Any]:
    return get_rag_service().load_pdf(file_path)


def split_documents(documents: list[Any]) -> list[Any]:
    return get_rag_service().split_documents(documents)


def create_embeddings(chunks: list[Any]) -> tuple[list[str], list[list[float]]]:
    texts = [chunk.page_content for chunk in chunks if getattr(chunk, "page_content", "").strip()]
    vectors = get_rag_service().embedding_model.encode(texts, normalize_embeddings=True).tolist() if texts else []
    return texts, vectors


def store_embeddings(texts: list[str], embeddings: list[list[float]]) -> None:
    if not texts:
        raise ValueError("No texts provided for embedding storage.")

    ids: list[str] = []
    metadatas: list[dict[str, Any]] = []
    for index, text in enumerate(texts):
        chunk_id = get_rag_service()._chunk_id("manual", -1, index, text)
        ids.append(chunk_id)
        metadatas.append(
            {
                "source": "manual",
                "page": -1,
                "chunk_index": index,
                "char_count": len(text),
            }
        )

    get_rag_service().collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def retrieve_documents(query: str, n_results: int = 4) -> dict[str, Any]:
    chunks = get_rag_service().retrieve_documents(query, n_results=n_results)

    documents = [[chunk.text for chunk in chunks]]
    metadatas = [[{"source": chunk.source, "page": chunk.page} for chunk in chunks]]
    distances = [[chunk.score for chunk in chunks]]

    return {
        "documents": documents,
        "metadatas": metadatas,
        "distances": distances,
    }


def generate_summary(query: str, user_id: str | None = None) -> str:
    active_user = user_id or _settings.default_user_id
    response = get_rag_service().answer_query(query, user_id=active_user)
    return response.answer


def generate_short_summary(summary: str, channel: str = "whatsapp") -> str:
    return get_rag_service().generate_short_summary(summary, channel=channel)


__all__ = [
    "IngestionReport",
    "RAGError",
    "RAGResponse",
    "RAGService",
    "RetrievedChunk",
    "get_rag_service",
    "list_pdf_files",
    "ingest_pdfs",
    "load_pdf",
    "split_documents",
    "create_embeddings",
    "store_embeddings",
    "retrieve_documents",
    "generate_summary",
    "generate_short_summary",
]
