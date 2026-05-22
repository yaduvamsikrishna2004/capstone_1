# vector_store

Lightweight vector store for small projects. Stores vectors and metadata to `store.pkl`.

Usage:

```py
from vector_store import VectorStore

vs = VectorStore()
vs.add("doc1", [0.1, 0.2, 0.3], {"title": "Doc 1"})
results = vs.search([0.1, 0.2, 0.25], k=3)
print(results)
```
