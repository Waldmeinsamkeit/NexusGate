from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexusgate.memory.models import MemoryCandidate
from nexusgate.memory.policies import SUCCESS_NEGATIVE_HINTS, SUCCESS_POSITIVE_HINTS
from nexusgate.memory.selector import MemorySelector

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
    SESSION_RECALL_SKILL_FILE = "session_memory_recall.md"
    SKILL_MANIFEST_FILE = "skill_manifest.json"
    SKILL_INDEX_SESSION_ID = "__skills__"
    SESSION_RECALL_TRIGGER_TERMS = (
        "\u56de\u5fc6",
        "\u4e4b\u524d",
        "\u4e0a\u6b21",
        "\u5386\u53f2",
        "\u4e0a\u4e0b\u6587",
        "session",
        "raw session",
        "l4",
    )

    def __init__(
        self,
        enabled: bool = True,
        store_path: str = "memory",
        source_root: str = ".",
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
        self.l4_dir = self.workspace / "l4"
        self.l4_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir = self.workspace / "candidates"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_archive_path = self.candidates_dir / "candidates.jsonl"
        self.candidates_state_path = self.candidates_dir / "candidate_states.json"
        self.l4_archive_path = self.l4_dir / "archive.jsonl"
        self.sop_path = self.workspace / "memory_management_sop.md"
        self.l1_path = self.workspace / "global_mem_insight.txt"
        self.l2_path = self.workspace / "global_mem.txt"
        self._bootstrap_files()
        self.l0_rules = self.load_l0_sop()
        self.selector = MemorySelector()
        self.skill_manifest = self._load_skill_manifest()
        self.store = _MemoryStore(
            self.workspace / "chroma",
            collection_name=collection_name,
            use_chroma=use_chroma,
        )
        self._hydrate_l4_from_file()
        self._index_l3_skills()

    def _bootstrap_files(self) -> None:
        self._copy_if_missing(
            self.source_root / "memory" / "memory_management_sop.md",
            self.sop_path,
            "No Execution, No Memory.\nDo not store volatile state.\n",
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
        self._copy_if_missing(
            self.source_root / "memory" / self.SKILL_MANIFEST_FILE,
            self.workspace / self.SKILL_MANIFEST_FILE,
            json.dumps(
                [
                    {
                        "name": "session_memory_recall",
                        "path": "session_memory_recall.md",
                        "triggers": ["回忆", "之前", "上次", "历史", "session", "l4", "context"],
                        "task_types": ["retrieval-only", "debug", "planning", "chat"],
                        "injection_mode": "summary",
                        "max_chars": 600,
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
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
        blocked = ("session id", "timestamp", "pid", "temp", "tmp", "current time")
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
        for root in (self.workspace, self.source_root / "memory", self.l3_dir):
            path = root / name
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8")
                except Exception:
                    return ""
        return ""

    def _load_skill_manifest(self) -> list[dict[str, Any]]:
        raw = self.load_l3_doc(self.SKILL_MANIFEST_FILE).strip()
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except Exception:
            return []

        rows: list[dict[str, Any]]
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict) and isinstance(payload.get("skills"), list):
            rows = payload["skills"]
        else:
            return []

        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            path = str(row.get("path") or "").strip()
            if not name or not path:
                continue
            normalized.append(row)
        return normalized

    def should_inject_session_recall(self, query: str) -> bool:
        lowered = (query or "").lower()
        return any(term in lowered for term in self.SESSION_RECALL_TRIGGER_TERMS)

    def _index_l3_skills(self) -> None:
        for entry in self.skill_manifest:
            payload = self._build_skill_payload(entry)
            if not payload:
                continue
            self.store.add(
                layer="L3",
                session_id=self.SKILL_INDEX_SESSION_ID,
                text=payload,
                evidence="tool:file_read",
                source=f"skill_bootstrap:{entry.get('name', 'unknown')}",
            )

    def _build_skill_payload(self, entry: dict[str, Any]) -> str:
        raw = self._load_skill_raw(entry).strip()
        if not raw:
            return ""
        metadata, body = self._parse_skill_markdown(raw)
        skill = str(entry.get("name") or metadata.get("key") or "").strip()
        if not skill:
            return ""
        summary = (
            str(entry.get("summary") or "").strip()
            or metadata.get("one_line_summary")
            or metadata.get("description")
            or "skill summary unavailable"
        )
        tags = self._to_csv(entry.get("tags")) or metadata.get("tags") or "skill"
        task_types = self._to_csv(entry.get("task_types")) or "chat"
        triggers = self._to_csv(entry.get("triggers")) or skill
        when = self._extract_markdown_section(body, "When to use")
        rules = self._extract_markdown_section(body, "Core rules")
        lines = [
            f"skill: {skill}",
            f"summary: {summary}",
            f"tags: {tags}",
            f"task_types: {task_types}",
            f"triggers: {triggers}",
            f"when: {when or 'recover prior conversation context'}",
            f"rules: {rules or 'only trust tool-verified artifacts'}",
        ]
        return "\n".join(lines)

    def _load_skill_raw(self, entry: dict[str, Any]) -> str:
        path_value = str(entry.get("path") or "").strip()
        if not path_value:
            return ""
        path = Path(path_value)
        candidates: list[Path] = []
        if path.is_absolute():
            candidates.append(path)
        else:
            candidates.extend(
                [
                    self.workspace / path,
                    self.source_root / "memory" / path,
                    self.l3_dir / path,
                ]
            )
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                return candidate.read_text(encoding="utf-8")
            except Exception:
                return ""
        return ""

    @staticmethod
    def _parse_skill_markdown(raw: str) -> tuple[dict[str, str], str]:
        if not raw.startswith("---"):
            return {}, raw
        parts = raw.split("---", 2)
        if len(parts) < 3:
            return {}, raw
        frontmatter = parts[1]
        body = parts[2].strip()
        metadata: dict[str, str] = {}
        current_key = ""
        current_list: list[str] = []
        for line in frontmatter.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- ") and current_key:
                current_list.append(stripped[2:].strip())
                metadata[current_key] = ", ".join(current_list)
                continue
            if ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            current_key = key.strip()
            current_list = []
            metadata[current_key] = value.strip()
        return metadata, body

    @staticmethod
    def _extract_markdown_section(body: str, heading: str) -> str:
        pattern = rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
        match = re.search(pattern, body)
        if not match:
            return ""
        text = " ".join(line.strip() for line in match.group(1).splitlines() if line.strip())
        return text[:320]

    @staticmethod
    def _merge_skill_blocks(*blocks: str) -> str:
        unique: list[str] = []
        for block in blocks:
            if not block or block == "(empty)":
                continue
            if block not in unique:
                unique.append(block)
        return "\n\n".join(unique) if unique else "(empty)"

    @staticmethod
    def _to_csv(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return ", ".join(items)
        return ""

    def _select_global_skill_names(self, query: str) -> list[str]:
        lowered = (query or "").lower()
        task_type = self.selector.classify_task(query)
        selected: list[str] = []
        for entry in self.skill_manifest:
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            task_types = [str(t).strip().lower() for t in entry.get("task_types", []) if str(t).strip()]
            if task_types and task_type not in task_types and "*" not in task_types:
                continue
            triggers = [str(t).strip().lower() for t in entry.get("triggers", []) if str(t).strip()]
            if triggers and not any(token in lowered for token in triggers):
                continue
            selected.append(name)
        if self.should_inject_session_recall(query) and "session_memory_recall" not in selected:
            selected.append("session_memory_recall")
        return selected

    def _build_relevant_skills(self, session_id: str, query: str) -> str:
        session_skills = self.query_memory(session_id, query, layers=["L3"])
        global_blocks: list[str] = []
        for skill_name in self._select_global_skill_names(query):
            block = self.query_memory(self.SKILL_INDEX_SESSION_ID, skill_name, layers=["L3"])
            if block != "(empty)":
                global_blocks.append(block)
        global_skills = self._merge_skill_blocks(*global_blocks)
        return self._merge_skill_blocks(session_skills, global_skills)

    def query_memory(self, session_id: str, query: str, layers: list[str]) -> str:
        rows = self.store.query(
            query_text=query,
            layers=layers,
            session_id=session_id,
            limit=self.top_k,
        )
        return "\n".join(rows) if rows else "(empty)"

    def build_memory_header(self, session_id: str, query: str) -> str:
        selected = self.selector.select(
            user_text=query,
            l0="\n".join(self.l0_rules.splitlines()[:12]).strip(),
            l1=self.load_l1_index(),
            l2=self.query_memory(session_id, query, layers=["L2"]),
            l3=self._build_relevant_skills(session_id, query),
            l4=self.query_memory(session_id, query, layers=["L4"]),
        )
        return (
            f"{selected.l0}\n\n"
            f"<memory_index>\n{selected.l1}\n</memory_index>\n\n"
            f"<relevant_skills>\n{selected.l3}\n</relevant_skills>\n\n"
            f"<session_recall_hints>\n{selected.l4}\n</session_recall_hints>\n\n"
            f"<relevant_memory>\n{selected.l2}\n</relevant_memory>"
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
            self._append_l4_archive(session_id=session_id, summary=summary)

    def distill_to_l4(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        self.archive_session(session_id=session_id, messages=messages)

    def start_memory_update(self, session_id: str, messages: list[dict[str, Any]], final_result: str) -> None:
        if not self.enabled:
            return
        self.archive_session(session_id=session_id, messages=messages)
        candidates = self._extract_memory_candidates(
            session_id=session_id,
            messages=messages,
            final_result=final_result,
        )
        pending = self._persist_candidates(candidates)
        self._commit_candidates(pending)
        self._gc_candidate_pool()

    def _extract_memory_candidates(
        self,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
        final_result: str,
    ) -> list[MemoryCandidate]:
        now = datetime.now(timezone.utc).isoformat()
        candidates: list[MemoryCandidate] = []

        session_summary = self._build_session_summary(messages=messages, final_result=final_result)
        if session_summary:
            candidates.append(
                MemoryCandidate(
                    session_id=session_id,
                    suggested_layer="L4",
                    kind="session_summary",
                    content=session_summary,
                    evidence="tool:archive_success",
                    source="session_summary",
                    verified=False,
                    created_at=now,
                )
            )

        if not self._looks_successful(final_result):
            return candidates

        for fact in self._extract_l2_fact_candidates(messages=messages, final_result=final_result):
            candidates.append(
                MemoryCandidate(
                    session_id=session_id,
                    suggested_layer="L2",
                    kind="fact_candidate",
                    content=fact,
                    evidence="tool:success",
                    source="stable_fact",
                    verified=True,
                    confidence=0.8,
                    created_at=now,
                )
            )

        takeaway = self._build_l3_task_takeaways(messages=messages, final_result=final_result)
        if takeaway:
            candidates.append(
                MemoryCandidate(
                    session_id=session_id,
                    suggested_layer="L3",
                    kind="task_takeaway",
                    content=takeaway,
                    evidence="tool:success",
                    source="task_takeaway",
                    verified=True,
                    confidence=0.7,
                    created_at=now,
                )
            )

        pointer = self._build_l1_pointer()
        if pointer:
            candidates.append(
                MemoryCandidate(
                    session_id=session_id,
                    suggested_layer="L1",
                    kind="index_pointer",
                    content=pointer,
                    evidence="tool:success",
                    source="l1_pointer",
                    verified=True,
                    confidence=0.6,
                    created_at=now,
                )
            )
        return candidates

    def _persist_candidates(self, candidates: list[MemoryCandidate]) -> list[MemoryCandidate]:
        if not candidates:
            return []
        states = self._load_candidate_states()
        now = datetime.now(timezone.utc).isoformat()
        pending: list[MemoryCandidate] = []
        seen_ids: set[str] = set()
        for row in candidates:
            row.candidate_id = self._candidate_id(row)
            if row.candidate_id in seen_ids:
                continue
            seen_ids.add(row.candidate_id)
            if row.candidate_id in states:
                continue
            if not row.created_at:
                row.created_at = now
            row.status = "pending"
            row.updated_at = now
            states[row.candidate_id] = asdict(row)
            pending.append(row)
        self._save_candidate_states(states)
        self._append_candidate_archive(pending)
        return pending

    def _commit_candidates(self, candidates: list[MemoryCandidate]) -> None:
        if not candidates:
            return
        states = self._load_candidate_states()
        finished: list[MemoryCandidate] = []
        for row in candidates:
            now = datetime.now(timezone.utc).isoformat()
            if not self._candidate_allowed(row):
                row.status = "rejected"
                row.rejected_reason = "validation_failed"
                row.updated_at = now
                states[row.candidate_id] = asdict(row)
                finished.append(row)
                continue
            self.upsert_memory(
                layer=row.suggested_layer,
                session_id=row.session_id,
                text=row.content,
                evidence=row.evidence,
                source=row.source,
            )
            row.status = "committed"
            row.updated_at = now
            states[row.candidate_id] = asdict(row)
            finished.append(row)
        self._save_candidate_states(states)
        self._append_candidate_archive(finished)

    def _candidate_allowed(self, row: MemoryCandidate) -> bool:
        layer = row.suggested_layer.upper()
        content = row.content.strip()
        evidence = row.evidence.strip()
        verified = row.verified
        if not content:
            return False
        if layer in {"L1", "L2", "L3"}:
            if not verified:
                return False
            return self.validate_memory_write(content, evidence)
        if layer == "L4":
            return True
        return False

    def _candidate_id(self, row: MemoryCandidate) -> str:
        normalized = re.sub(r"\s+", " ", row.content.strip().lower())
        payload = "|".join(
            [
                row.session_id,
                row.suggested_layer.upper(),
                row.kind.strip().lower(),
                normalized,
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def _load_candidate_states(self) -> dict[str, dict[str, Any]]:
        if not self.candidates_state_path.exists():
            return {}
        try:
            payload = json.loads(self.candidates_state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}

    def _save_candidate_states(self, states: dict[str, dict[str, Any]]) -> None:
        self.candidates_state_path.write_text(
            json.dumps(states, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _append_candidate_archive(self, candidates: list[MemoryCandidate]) -> None:
        if not candidates:
            return
        with self.candidates_archive_path.open("a", encoding="utf-8") as handle:
            for row in candidates:
                handle.write(f"{json.dumps(asdict(row), ensure_ascii=False)}\n")

    def _gc_candidate_pool(self, max_states: int = 2000, max_archive_lines: int = 4000) -> None:
        states = self._load_candidate_states()
        if len(states) > max_states:
            ordered = sorted(
                states.values(),
                key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""),
                reverse=True,
            )
            kept = ordered[:max_states]
            states = {str(row.get("candidate_id")): row for row in kept if row.get("candidate_id")}
            self._save_candidate_states(states)

        if not self.candidates_archive_path.exists():
            return
        try:
            lines = self.candidates_archive_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return
        if len(lines) <= max_archive_lines:
            return
        trimmed = lines[-max_archive_lines:]
        self.candidates_archive_path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")

    @staticmethod
    def _looks_successful(final_result: str) -> bool:
        lowered = final_result.lower()
        if any(token in lowered for token in SUCCESS_NEGATIVE_HINTS):
            return False
        return any(token in lowered for token in SUCCESS_POSITIVE_HINTS)

    def _build_session_summary(self, messages: list[dict[str, Any]], final_result: str) -> str:
        latest_user = self._extract_latest_message(messages, "user")
        latest_assistant = self._extract_latest_message(messages, "assistant")
        parts = [
            f"[USER] {latest_user[:200] or 'unknown'}",
            f"[Agent] {latest_assistant[:200] or 'unknown'}",
            f"[RESULT] {final_result[:200] or 'unknown'}",
        ]
        return "\n".join(parts)

    def _extract_l2_fact_candidates(self, messages: list[dict[str, Any]], final_result: str) -> list[str]:
        pool = [final_result, self._extract_latest_message(messages, "assistant")]
        facts: list[str] = []
        patterns = [
            r"(?:file|path)\s+([A-Za-z0-9_./\\-]+)",
            r"(?:port|timeout|retries)\s*(?:is|=)\s*([A-Za-z0-9_.-]+)",
            r"(?:config|env)\s*[:=]\s*([A-Za-z0-9_./\\-]+)",
        ]
        for text in pool:
            lowered = text.lower()
            if not lowered:
                continue
            for pattern in patterns:
                for match in re.findall(pattern, text, flags=re.IGNORECASE):
                    value = match.strip()
                    if not value:
                        continue
                    facts.append(f"stable_fact: {value}")
            if "test passed" in lowered or "tests passed" in lowered:
                facts.append("stable_fact: tests passed")
        unique: list[str] = []
        for row in facts:
            if row not in unique:
                unique.append(row)
        return unique

    def _build_l3_task_takeaways(self, messages: list[dict[str, Any]], final_result: str) -> str:
        latest_user = self._extract_latest_message(messages, "user")
        latest_assistant = self._extract_latest_message(messages, "assistant")
        if not latest_user and not latest_assistant and not final_result:
            return ""
        return (
            "task_takeaway: "
            f"goal={latest_user[:80] or 'unknown'}; "
            f"action={latest_assistant[:80] or 'unknown'}; "
            f"result={final_result[:80] or 'unknown'}"
        )

    @staticmethod
    def _build_l1_pointer() -> str:
        return "memory_write_rules -> L2; session_recall -> L4; task_takeaway -> L3"

    @staticmethod
    def _extract_latest_message(messages: list[dict[str, Any]], role: str) -> str:
        for msg in reversed(messages):
            if msg.get("role") != role:
                continue
            content = msg.get("content")
            if isinstance(content, str):
                return content.replace("\n", " ").strip()
            return json.dumps(content, ensure_ascii=False)
        return ""

    def persist_turn(self, request_payload: dict[str, Any], response_payload: dict[str, Any]) -> None:
        metadata = request_payload.get("metadata") or {}
        session_id = metadata.get("session_id", "default")
        messages = request_payload.get("messages") or []
        final_text = self._extract_response_text(response_payload)
        self.start_memory_update(session_id=session_id, messages=messages, final_result=final_text)

    def _append_l4_archive(self, session_id: str, summary: str) -> None:
        row = {
            "session_id": session_id,
            "summary": summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        line = json.dumps(row, ensure_ascii=False)
        if not self.l4_archive_path.exists():
            self.l4_archive_path.write_text(f"{line}\n", encoding="utf-8")
            return
        with self.l4_archive_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

    def _hydrate_l4_from_file(self) -> None:
        if not self.l4_archive_path.exists():
            return
        try:
            lines = self.l4_archive_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            session_id = str(row.get("session_id") or "default")
            summary = str(row.get("summary") or "").strip()
            if not summary:
                continue
            self.store.add(
                layer="L4",
                session_id=session_id,
                text=summary,
                evidence="tool:archive_replay",
                source="archive_file",
            )

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

