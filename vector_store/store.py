import os
import pickle
import math
from typing import Any, Dict, List, Optional


class VectorStore:
    """A lightweight file-backed vector store with cosine similarity search.

    Stores items as a list of records: {'id': str, 'vector': list[float], 'metadata': dict}
    Persists to `store.pkl` in the same package directory.
    """

    def __init__(self, persist_path: Optional[str] = None):
        base_dir = os.path.dirname(__file__)
        self.persist_path = persist_path or os.path.join(base_dir, "store.pkl")
        self._items: List[Dict[str, Any]] = []
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self.load()

    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector with an identifier and optional metadata."""
        self._ensure_loaded()
        self._items.append({"id": id, "vector": list(vector), "metadata": metadata or {}})
        self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        with open(self.persist_path, "wb") as f:
            pickle.dump(self._items, f)

    def load(self) -> None:
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "rb") as f:
                    self._items = pickle.load(f)
            except Exception:
                self._items = []
        else:
            self._items = []
        self._loaded = True

    def clear(self) -> None:
        """Clear all stored items and persist empty store."""
        self._items = []
        self.save()

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def search(self, query_vector: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """Return up to `k` nearest items to `query_vector` ordered by descending similarity.

        Each returned dict contains: 'id', 'score', 'metadata'.
        """
        self._ensure_loaded()
        scored = []
        for item in self._items:
            score = self._cosine_similarity(query_vector, item["vector"]) 
            scored.append({"id": item["id"], "score": score, "metadata": item.get("metadata", {})})
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:k]
