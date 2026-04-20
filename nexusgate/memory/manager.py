from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:  # pragma: no cover
    chromadb = None
    SentenceTransformerEmbeddingFunction = None


class _MemoryStore:
    def __init__(
        self,
        db_path: Path,
        collection_name: str,
        use_chroma: bool,
        embed_model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._docs: list[dict[str, Any]] = []
        self._collection = None
        if not use_chroma or chromadb is None:
            return

        try:
            db_path.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(db_path))
            embed_fn = None
            if SentenceTransformerEmbeddingFunction is not None:
                embed_fn = SentenceTransformerEmbeddingFunction(model_name=embed_model_name)
            if embed_fn is not None:
                self._collection = client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=embed_fn,
                )
                return
            self._collection = client.get_or_create_collection(name=collection_name)
        except BaseException:
            self._collection = None

    def add(self, *, layer: str, session_id: str, text: str, evidence: str, source: str) -> None:
        item_id = hashlib.sha1(f"{layer}:{session_id}:{text}".encode("utf-8")).hexdigest()
        metadata = {
            "layer": layer,
            "session_id": session_id,
            "evidence": evidence,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._collection is not None:
            self._collection.upsert(ids=[item_id], documents=[text], metadatas=[metadata])
            return
        self._docs = [doc for doc in self._docs if doc["id"] != item_id]
        self._docs.append({"id": item_id, "text": text, "metadata": metadata})

    def query(self, *, query_text: str, layers: list[str], session_id: str | None, limit: int) -> list[str]:
        if self._collection is not None:
            where: dict[str, Any] = {"layer": {"$in": layers}}
            if session_id:
                where = {"$and": [where, {"session_id": session_id}]}
            result = self._collection.query(
                query_texts=[query_text or "recent memory"],
                n_results=limit,
                where=where,
            )
            docs = (result.get("documents") or [[]])[0]
            metas = (result.get("metadatas") or [[]])[0]
            return [f"[{meta.get('layer', 'L?')}] {doc}" for doc, meta in zip(docs, metas)]

        candidates = []
        for row in self._docs:
            meta = row["metadata"]
            if meta.get("layer") not in layers:
                continue
            if session_id and meta.get("session_id") != session_id:
                continue
            score = 2 if query_text and query_text in row["text"] else 1
            candidates.append((score, row))
        candidates.sort(key=lambda item: item[0], reverse=True)
        sliced = [row for _, row in candidates[:limit]]
        return [f"[{row['metadata'].get('layer', 'L?')}] {row['text']}" for row in sliced]


class MemoryManager:
    def __init__(
        self,
        enabled: bool = True,
        store_path: str = "memory",
        source_root: str = "F:/repo/GenericAgent",
        collection_name: str = "nexusgate_memory",
        top_k: int = 6,
        use_chroma: bool = True,
    ) -> None:
        self.enabled = enabled
        self.top_k = top_k
        self.source_root = Path(source_root)
        self.workspace = Path(store_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.l3_dir = self.workspace / "l3"
        self.l3_dir.mkdir(parents=True, exist_ok=True)
        self.sop_path = self.workspace / "memory_management_sop.md"
        self.l1_path = self.workspace / "global_mem_insight.txt"
        self.l2_path = self.workspace / "global_mem.txt"
        self._bootstrap_files()
        self.l0_rules = self.load_l0_sop()
        self.store = _MemoryStore(
            self.workspace / "chroma",
            collection_name=collection_name,
            use_chroma=use_chroma,
        )

    def _bootstrap_files(self) -> None:
        self._copy_if_missing(
            self.source_root / "memory" / "memory_management_sop.md",
            self.sop_path,
            "No Execution, No Memory.\n禁止存储易变状态。\n",
        )
        l1_seed = self._load_template(
            self.source_root / "assets" / "insight_fixed_structure.txt",
            "# [Global Memory Insight]\n",
        )
        self._copy_if_missing(
            self.source_root / "assets" / "global_mem_insight_template.txt",
            self.l1_path,
            l1_seed,
        )
        self._copy_if_missing(
            self.source_root / "memory" / "global_mem.txt",
            self.l2_path,
            "## [FACTS]\n",
        )

    @staticmethod
    def _load_template(path: Path, default_value: str) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return default_value

    @staticmethod
    def _copy_if_missing(src: Path, dst: Path, fallback: str) -> None:
        if dst.exists():
            return
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            return
        dst.write_text(fallback, encoding="utf-8")

    def load_l0_sop(self) -> str:
        return self.sop_path.read_text(encoding="utf-8")

    def validate_memory_write(self, candidate_text: str, evidence: str) -> bool:
        if not candidate_text.strip() or not evidence.strip():
            return False
        blocked = ("session id", "timestamp", "pid", "临时", "tmp", "当前时间")
        lowered = candidate_text.lower()
        if any(token in lowered for token in blocked):
            return False
        verified = ("success", "ok", "pass", "tool:", "shell", "file", "archive")
        return any(token in evidence.lower() for token in verified)

    def load_l1_index(self) -> str:
        return self.l1_path.read_text(encoding="utf-8")

    def load_l2_facts(self, section: str | None = None) -> str:
        content = self.l2_path.read_text(encoding="utf-8")
        if not section:
            return content
        marker = f"## [{section}]"
        if marker not in content:
            return ""
        chunk = content.split(marker, maxsplit=1)[1]
        return chunk.split("## [", maxsplit=1)[0].strip()

    def load_l3_doc(self, name: str) -> str:
        for root in (self.source_root / "memory", self.l3_dir):
            path = root / name
            if path.exists():
                return path.read_text(encoding="utf-8")
        return ""

    def query_memory(self, session_id: str, query: str, layers: list[str]) -> str:
        rows = self.store.query(
            query_text=query,
            layers=layers,
            session_id=session_id,
            limit=self.top_k,
        )
        return "\n".join(rows) if rows else "(empty)"

    def build_memory_header(self, session_id: str, query: str) -> str:
        l0_excerpt = "\n".join(self.l0_rules.splitlines()[:12]).strip()
        l1_index = self.load_l1_index()
        relevant = self.query_memory(session_id, query, layers=["L1", "L2", "L3", "L4"])
        return (
            f"{l0_excerpt}\n\n"
            f"<memory_index>\n{l1_index}\n</memory_index>\n\n"
            f"<relevant_memory>\n{relevant}\n</relevant_memory>"
        )

    def build_memory_system_prompt(self, session_id: str, query: str) -> str:
        return self.build_memory_header(session_id=session_id, query=query)

    def get_memory(self, session_id: str, query: str) -> str:
        return self.build_memory_header(session_id=session_id, query=query)

    def enrich_messages(self, messages: list[dict[str, Any]], metadata: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not self.enabled:
            return messages
        session_id = (metadata or {}).get("session_id", "default")
        query = (metadata or {}).get("query") or self._extract_latest_user_query(messages)
        memory_header = self.build_memory_system_prompt(session_id=session_id, query=query)
        memory_msg = {"role": "system", "content": f"<nexus_context>\n{memory_header}\n</nexus_context>"}
        return [memory_msg, *messages]

    @staticmethod
    def _extract_latest_user_query(messages: list[dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                return json.dumps(content, ensure_ascii=False)
        return "default_query"

    def classify_memory_item(self, item: dict[str, Any]) -> str:
        kind = item.get("kind")
        if kind in {"rule", "index"}:
            return "L1"
        if kind == "fact":
            return "L2"
        if kind == "task":
            return "L3"
        if kind == "archive":
            return "L4"
        return "drop"

    def upsert_memory(self, layer: str, session_id: str, text: str, evidence: str, source: str = "manual") -> bool:
        if not self.validate_memory_write(text, evidence):
            return False
        self.store.add(layer=layer, session_id=session_id, text=text, evidence=evidence, source=source)
        self._sync_files(layer=layer, text=text)
        return True

    def _sync_files(self, layer: str, text: str) -> None:
        if layer == "L1":
            self._append_unique(self.l1_path, text)
        if layer == "L2":
            self._append_unique(self.l2_path, f"- {text}")

    @staticmethod
    def _append_unique(path: Path, line: str) -> None:
        content = path.read_text(encoding="utf-8")
        if line in content:
            return
        path.write_text(f"{content.rstrip()}\n{line}\n", encoding="utf-8")

    def extract_key_history(self, messages: list[dict[str, Any]]) -> list[str]:
        history: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            text = text.replace("\n", " ").strip()
            if role == "user":
                history.append(f"[USER] {text[:240]}")
            elif role == "assistant":
                history.append(f"[Agent] {text[:240]}")
        return history

    def archive_raw_session(self, messages: list[dict[str, Any]]) -> str:
        return "\n".join(self.extract_key_history(messages))

    def archive_session(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        summary = self.archive_raw_session(messages)
        if summary:
            self.upsert_memory(
                layer="L4",
                session_id=session_id,
                text=summary,
                evidence="tool:archive_success",
                source="archive_session",
            )

    def distill_to_l4(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        self.archive_session(session_id=session_id, messages=messages)

    def start_memory_update(self, session_id: str, messages: list[dict[str, Any]], final_result: str) -> None:
        if not self.enabled:
            return
        self.archive_session(session_id=session_id, messages=messages)
        if self._looks_successful(final_result):
            self.upsert_memory(
                layer="L2",
                session_id=session_id,
                text=f"会话结果: {final_result[:320]}",
                evidence="tool:success",
                source="final_result",
            )
            self.upsert_memory(
                layer="L1",
                session_id=session_id,
                text="recent_success -> L2",
                evidence="tool:success",
                source="l1_pointer",
            )

    @staticmethod
    def _looks_successful(final_result: str) -> bool:
        hints = ("成功", "完成", "通过", "done", "success")
        lowered = final_result.lower()
        return any(token in lowered for token in hints)

    def persist_turn(self, request_payload: dict[str, Any], response_payload: dict[str, Any]) -> None:
        metadata = request_payload.get("metadata") or {}
        session_id = metadata.get("session_id", "default")
        messages = request_payload.get("messages") or []
        final_text = self._extract_response_text(response_payload)
        self.start_memory_update(session_id=session_id, messages=messages, final_result=final_text)

    @staticmethod
    def _extract_response_text(response_payload: dict[str, Any]) -> str:
        try:
            choices = response_payload.get("choices") or []
            message = (choices[0].get("message") or {}) if choices else {}
            content = message.get("content") or ""
            if isinstance(content, str):
                return content
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return ""
