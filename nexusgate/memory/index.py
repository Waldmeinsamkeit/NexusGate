from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from nexusgate.memory.schema import MemoryRecord, QueryFilters

try:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:  # pragma: no cover
    chromadb = None
    SentenceTransformerEmbeddingFunction = None


@dataclass(slots=True)
class MemoryBackendStatus:
    repository_ok: bool
    index_backend: str
    index_ready: bool
    degrade_reason: str = ""


class MemoryIndex(Protocol):
    def upsert(self, records: list[MemoryRecord]) -> None: ...
    def delete(self, memory_ids: list[str]) -> None: ...
    def query(self, query: str, filters: QueryFilters, limit: int) -> list[str]: ...
    def health(self) -> MemoryBackendStatus: ...


class NullIndex:
    def upsert(self, records: list[MemoryRecord]) -> None:
        return None

    def delete(self, memory_ids: list[str]) -> None:
        return None

    def query(self, query: str, filters: QueryFilters, limit: int) -> list[str]:
        return []

    def health(self) -> MemoryBackendStatus:
        return MemoryBackendStatus(repository_ok=True, index_backend="null", index_ready=False, degrade_reason="disabled")


class ChromaIndex:
    def __init__(
        self,
        persist_dir: Path,
        collection_name: str,
        embedding_model: str | None = None,
    ) -> None:
        self._degrade_reason = ""
        self._collection = None
        if chromadb is None:
            self._degrade_reason = "chromadb_unavailable"
            return
        try:
            persist_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(persist_dir))
            embed_fn = None
            if embedding_model and SentenceTransformerEmbeddingFunction is not None:
                embed_fn = SentenceTransformerEmbeddingFunction(model_name=embedding_model)
            self._collection = (
                client.get_or_create_collection(name=collection_name, embedding_function=embed_fn)
                if embed_fn is not None
                else client.get_or_create_collection(name=collection_name)
            )
        except BaseException as exc:
            self._degrade_reason = str(exc)
            self._collection = None

    def upsert(self, records: list[MemoryRecord]) -> None:
        if self._collection is None or not records:
            return
        self._collection.upsert(
            ids=[row.memory_id for row in records],
            documents=[row.content for row in records],
            metadatas=[
                {"layer": row.layer, "scope": row.scope, "session_id": row.session_id, "project_id": row.project_id}
                for row in records
            ],
        )

    def delete(self, memory_ids: list[str]) -> None:
        if self._collection is None or not memory_ids:
            return
        self._collection.delete(ids=memory_ids)

    def query(self, query: str, filters: QueryFilters, limit: int) -> list[str]:
        if self._collection is None:
            return []
        where: dict[str, object] = {"layer": {"$in": filters.layers}} if filters.layers else {}
        if filters.session_id:
            where = {"$and": [where, {"session_id": filters.session_id}]} if where else {"session_id": filters.session_id}
        if filters.project_id:
            where = {"$and": [where, {"project_id": filters.project_id}]} if where else {"project_id": filters.project_id}
        result = self._collection.query(query_texts=[query or "recent memory"], n_results=limit, where=where or None)
        rows = (result.get("ids") or [[]])[0]
        return [str(row) for row in rows]

    def health(self) -> MemoryBackendStatus:
        ready = self._collection is not None
        return MemoryBackendStatus(
            repository_ok=True,
            index_backend="chroma",
            index_ready=ready,
            degrade_reason=self._degrade_reason if not ready else "",
        )
