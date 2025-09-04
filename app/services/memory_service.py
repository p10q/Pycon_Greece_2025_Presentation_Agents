"""Vector memory service using ChromaDB (optional, degrades gracefully).

This service stores conversational interactions so future prompts can be
augmented with relevant context. If Chroma or OpenAI embeddings are not
available, it falls back to an in-memory list to avoid breaking the app.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MemoryRecord:
    id: str
    text: str
    metadata: dict[str, Any]


class MemoryService:
    """Abstraction over a vector store for chat memories."""

    def __init__(self, persist_dir: Path | None = None) -> None:
        self.persist_dir = persist_dir
        self._enabled = False
        self._client = None
        self._collection = None
        self._fallback: list[MemoryRecord] = []
        self._initialize()

    def _initialize(self) -> None:
        try:
            import chromadb  # type: ignore
            from chromadb.utils.embedding_functions import (
                OpenAIEmbeddingFunction,  # type: ignore
            )

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # No embeddings without an API key; keep fallback mode
                return

            persist_path = str(self.persist_dir) if self.persist_dir else None
            self._client = (
                chromadb.PersistentClient(path=persist_path)
                if persist_path
                else chromadb.Client()
            )
            embedding_fn = OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-small",
            )
            self._collection = self._client.get_or_create_collection(
                name="chat_memory",
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            self._enabled = True
        except Exception:
            # Any import/initialization failure results in fallback mode
            self._enabled = False

    # Public API ----------------------------------------------------------
    def add_interaction(
        self,
        user_input: str,
        response: str,
        *,
        kind: str = "chat",
    ) -> str | None:
        """Store a user-input/response pair as memory."""
        text = f"Q: {user_input}\nA: {response}"
        record_id = f"mem-{int(datetime.utcnow().timestamp()*1000)}"
        metadata = {
            "type": kind,
            "created_at": datetime.utcnow().isoformat(),
        }
        if self._enabled and self._collection is not None:
            try:
                self._collection.add(
                    ids=[record_id],
                    documents=[text],
                    metadatas=[metadata],
                )
                return record_id
            except Exception:
                # Fall through to in-memory fallback
                pass
        self._fallback.append(MemoryRecord(id=record_id, text=text, metadata=metadata))
        return record_id

    def search_memories(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Retrieve top-k similar memories to the given query."""
        if self._enabled and self._collection is not None:
            try:
                res = self._collection.query(query_texts=[query], n_results=k)
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                dists = res.get("distances", [[]])[0]
                out: list[dict[str, Any]] = []
                for doc, meta, dist in zip(docs, metas, dists, strict=False):
                    out.append(
                        {
                            "text": doc,
                            "metadata": meta or {},
                            "score": 1 - float(dist) if dist is not None else None,
                        },
                    )
                return out
            except Exception:
                pass
        # Fallback: naive substring scoring
        results: list[dict[str, Any]] = []
        for rec in self._fallback:
            score = 1.0 if query.lower() in rec.text.lower() else 0.0
            results.append({"text": rec.text, "metadata": rec.metadata, "score": score})
        results.sort(key=lambda r: r.get("score") or 0.0, reverse=True)
        return results[:k]


def build_default_memory_service(project_root: Path | None = None) -> MemoryService:
    root = project_root or Path(__file__).resolve().parents[2]
    persist_dir = root / "data" / "chroma_db"
    persist_dir.mkdir(parents=True, exist_ok=True)
    return MemoryService(persist_dir=persist_dir)
