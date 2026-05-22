from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ollama import Client as OllamaClient
from sentence_transformers import SentenceTransformer

from config import Settings
from utils import CHANNEL_LIMITS, fit_to_limit, normalize_whitespace

logger = logging.getLogger(__name__)


class RAGError(RuntimeError):
    """Raised when any RAG pipeline stage fails."""


@dataclass
class IngestionReport:
    files_processed: int
    chunks_created: int
    chunks_indexed: int
    chunks_skipped: int


@dataclass
class RetrievedChunk:
    text: str
    source: str
    page: int
    score: float


@dataclass
class RAGResponse:
    answer: str
    chunks: list[RetrievedChunk]


class RAGService:
    """
    Retrieval-Augmented Generation pipeline.

    Flow:
    1. Load PDFs.
    2. Split text into overlapping chunks.
    3. Create embeddings.
    4. Store vectors + metadata in Chroma.
    5. Retrieve semantically similar chunks for each user query.
    6. Generate grounded responses with Ollama.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedding_model = SentenceTransformer(settings.embedding_model_name)
        self.ollama_client = OllamaClient(host=settings.ollama_host)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        try:
            chroma_client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
            self.collection: Collection = chroma_client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "Capstone RAG document chunks"},
            )
        except Exception as error:
            logger.exception("Failed to initialize Chroma collection: %s", error)
            raise RAGError(str(error)) from error

        self.query_cache: dict[str, RAGResponse] = {}
        self.conversation_history: dict[str, list[dict[str, str]]] = {}

    def list_available_pdfs(self) -> list[Path]:
        return sorted(self.settings.documents_dir.glob("*.pdf"))

    def load_pdf(self, file_path: str | Path) -> list[Any]:
        path = Path(file_path)
        if not path.is_absolute():
            path = self.settings.project_root / path

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        try:
            loader = PyPDFLoader(str(path))
            documents = loader.load()
        except Exception as error:
            logger.exception("Failed to load PDF '%s': %s", path, error)
            raise RAGError(str(error)) from error

        if not documents:
            raise RAGError(f"No readable content in PDF: {path}")

        return documents

    def split_documents(self, documents: list[Any]) -> list[Any]:
        chunks = self.text_splitter.split_documents(documents)
        if not chunks:
            raise RAGError("Chunking produced zero chunks.")
        return chunks

    @staticmethod
    def _chunk_id(source: str, page: int, chunk_index: int, text: str) -> str:
        payload = f"{source}|{page}|{chunk_index}|{text}".encode("utf-8", errors="ignore")
        return hashlib.sha256(payload).hexdigest()

    def _existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()

        try:
            result = self.collection.get(ids=ids, include=[])
            return set(result.get("ids", []))
        except Exception:
            return set()

    def ingest_pdf(self, file_path: str | Path) -> IngestionReport:
        documents = self.load_pdf(file_path)
        chunks = self.split_documents(documents)

        chunk_texts: list[str] = []
        chunk_ids: list[str] = []
        metadatas: list[dict[str, Any]] = []

        source_name = Path(file_path).name

        for chunk_index, chunk in enumerate(chunks):
            text = normalize_whitespace(chunk.page_content)
            if not text:
                continue

            page = int(chunk.metadata.get("page", -1)) if chunk.metadata else -1
            chunk_id = self._chunk_id(source_name, page, chunk_index, text)

            chunk_texts.append(text)
            chunk_ids.append(chunk_id)
            metadatas.append(
                {
                    "source": source_name,
                    "page": page,
                    "chunk_index": chunk_index,
                    "char_count": len(text),
                }
            )

        if not chunk_texts:
            raise RAGError("All chunks were empty after normalization.")

        existing = self._existing_ids(chunk_ids)

        new_texts: list[str] = []
        new_ids: list[str] = []
        new_metadatas: list[dict[str, Any]] = []

        for i, chunk_id in enumerate(chunk_ids):
            if chunk_id in existing:
                continue
            new_texts.append(chunk_texts[i])
            new_ids.append(chunk_id)
            new_metadatas.append(metadatas[i])

        if new_texts:
            try:
                vectors = self.embedding_model.encode(new_texts, normalize_embeddings=True).tolist()
                self.collection.upsert(
                    ids=new_ids,
                    documents=new_texts,
                    embeddings=vectors,
                    metadatas=new_metadatas,
                )
            except Exception as error:
                logger.exception("Failed to index chunks in Chroma: %s", error)
                raise RAGError(str(error)) from error

        return IngestionReport(
            files_processed=1,
            chunks_created=len(chunk_texts),
            chunks_indexed=len(new_texts),
            chunks_skipped=len(chunk_texts) - len(new_texts),
        )

    def ingest_documents(self, file_paths: list[str | Path]) -> IngestionReport:
        total_processed = 0
        total_chunks = 0
        total_indexed = 0
        total_skipped = 0

        for file_path in file_paths:
            report = self.ingest_pdf(file_path)
            total_processed += report.files_processed
            total_chunks += report.chunks_created
            total_indexed += report.chunks_indexed
            total_skipped += report.chunks_skipped

        return IngestionReport(
            files_processed=total_processed,
            chunks_created=total_chunks,
            chunks_indexed=total_indexed,
            chunks_skipped=total_skipped,
        )

    def retrieve_documents(self, query: str, n_results: int = 4) -> list[RetrievedChunk]:
        clean_query = normalize_whitespace(query)
        if not clean_query:
            raise ValueError("Query cannot be empty.")

        try:
            query_embedding = self.embedding_model.encode([clean_query], normalize_embeddings=True).tolist()
            result = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as error:
            logger.exception("Vector retrieval failed: %s", error)
            raise RAGError(str(error)) from error

        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for doc_text, metadata, distance in zip(docs, metas, distances):
            metadata = metadata or {}
            chunks.append(
                RetrievedChunk(
                    text=doc_text,
                    source=str(metadata.get("source", "unknown")),
                    page=int(metadata.get("page", -1)),
                    score=float(distance),
                )
            )

        return chunks

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        context_blocks: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            context_blocks.append(
                f"[{idx}] source={chunk.source} page={chunk.page} score={chunk.score:.4f}\n{chunk.text}"
            )
        return "\n\n".join(context_blocks)

    def answer_query(self, query: str, user_id: str) -> RAGResponse:
        cache_key = f"{user_id}|{normalize_whitespace(query).lower()}"
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]

        retrieved = self.retrieve_documents(query)
        if not retrieved:
            answer = (
                "I could not find relevant context in the vector store. "
                "Please ingest one or more PDFs before asking questions."
            )
            response = RAGResponse(answer=answer, chunks=[])
            self.query_cache[cache_key] = response
            return response

        context = self._format_context(retrieved)

        prompt = (
            "You are a helpful RAG assistant. Answer only from the provided context. "
            "If information is missing, say that explicitly. Keep the answer concise but complete.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{query}\n\n"
            "Return:\n"
            "1) Direct answer\n"
            "2) Key points as short bullets\n"
            "3) Confidence note"
        )

        try:
            result = self.ollama_client.chat(
                model=self.settings.ollama_model,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = result["message"]["content"]
        except Exception as error:
            logger.exception("Ollama request failed: %s", error)
            raise RAGError(str(error)) from error

        response = RAGResponse(answer=answer, chunks=retrieved)
        self.query_cache[cache_key] = response

        history = self.conversation_history.setdefault(user_id, [])
        history.append({"query": query, "answer": answer})

        return response

    def generate_short_summary(self, full_answer: str, channel: str = "whatsapp") -> str:
        normalized_channel = channel.lower().strip()
        limit = CHANNEL_LIMITS.get(normalized_channel, 280)

        prompt = (
            f"Rewrite the following answer for {normalized_channel}. "
            f"Use plain text only and keep it under {limit} characters.\n\n"
            f"Answer:\n{full_answer}"
        )

        try:
            result = self.ollama_client.chat(
                model=self.settings.ollama_model,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = result["message"]["content"]
        except Exception:
            summary = full_answer

        return fit_to_limit(summary, limit)
