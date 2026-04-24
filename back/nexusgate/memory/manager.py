from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexusgate.memory.events import MemoryEvent, MemoryEventLogger
from nexusgate.memory.index import ChromaIndex, MemoryBackendStatus, MemoryIndex, NullIndex
from nexusgate.memory.models import DroppedMemoryCandidate, MemoryCandidate, MemoryPack, MemoryRetrievalResult, ScoredMemory
from nexusgate.memory.policies import SUCCESS_NEGATIVE_HINTS, SUCCESS_POSITIVE_HINTS
from nexusgate.memory.query_service import MemoryQueryService
from nexusgate.memory.repository import StructuredMemoryRepository
from nexusgate.memory.schema import MemoryCitation, MemoryRecord, MemoryScope, MemoryType, PendingMemoryRecord, QueryFilters
from nexusgate.memory.scoring import MemoryScorer
from nexusgate.memory.selector import MemorySelector
from nexusgate.memory.summarizer import MemorySummarizer
from nexusgate.memory.write_policy import MemoryWritePolicy


class MemoryManager:
    SESSION_RECALL_SKILL_FILE = "session_memory_recall.md"
    SKILL_MANIFEST_FILE = "skill_manifest.json"
    SKILL_INDEX_SESSION_ID = "__skills__"
    SESSION_RECALL_TRIGGER_TERMS = ("回忆", "之前", "上次", "历史", "session", "raw session", "l4")

    def __init__(
        self,
        enabled: bool = True,
        store_path: str = "memory",
        source_root: str = ".",
        collection_name: str = "nexusgate_memory",
        top_k: int = 6,
        use_chroma: bool = True,
        *,
        workspace: Path | None = None,
        repository: StructuredMemoryRepository | None = None,
        index: MemoryIndex | None = None,
        query_service: MemoryQueryService | None = None,
        summarizer: MemorySummarizer | None = None,
        write_policy: MemoryWritePolicy | None = None,
        event_logger: MemoryEventLogger | None = None,
        selector: MemorySelector | None = None,
    ) -> None:
        self.enabled = enabled
        self.top_k = top_k
        self.source_root = Path(source_root)
        self.workspace = workspace or Path(store_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.l3_dir = self.workspace / "l3"
        self.l3_dir.mkdir(parents=True, exist_ok=True)
        self.l4_dir = self.workspace / "l4"
        self.l4_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir = self.workspace / "candidates"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

        self.candidates_archive_path = self.candidates_dir / "candidates.jsonl"
        self.candidates_state_path = self.candidates_dir / "candidate_states.json"
        self.candidate_events_path = self.candidates_dir / "candidate_events.jsonl"
        self.l4_archive_path = self.l4_dir / "archive.jsonl"
        self.structured_memory_path = self.workspace / "structured_memory.jsonl"
        self.sop_path = self.workspace / "memory_management_sop.md"
        self.l1_path = self.workspace / "global_mem_insight.txt"
        self.l2_path = self.workspace / "global_mem.txt"

        self._bootstrap_files()
        self.l0_rules = self.load_l0_sop()
        self.write_policy = write_policy or MemoryWritePolicy()
        self.selector = selector or MemorySelector()
        self.repository = repository or StructuredMemoryRepository(self.structured_memory_path)
        if index is not None:
            self.index = index
        elif use_chroma:
            self.index = ChromaIndex(
                persist_dir=self.workspace / "chroma",
                collection_name=collection_name,
                embedding_model="all-MiniLM-L6-v2",
            )
        else:
            self.index = NullIndex()
        self.query_service = query_service or MemoryQueryService(
            repository=self.repository,
            index=self.index,
            scorer=MemoryScorer(),
        )
        self.summarizer = summarizer or MemorySummarizer(write_policy=self.write_policy)
        self.event_logger = event_logger or MemoryEventLogger(self.candidate_events_path)
        self.skill_manifest = self._load_skill_manifest()
        self._index_l3_skills()

    @property
    def backend_status(self) -> MemoryBackendStatus:
        return self.index.health()

    def _bootstrap_files(self) -> None:
        self._copy_if_missing(
            self.source_root / "memory" / "memory_management_sop.md",
            self.sop_path,
            "No Execution, No Memory.\nDo not store volatile state.\n",
        )
        l1_seed = self._load_template(self.source_root / "assets" / "insight_fixed_structure.txt", "# [Global Memory Insight]\n")
        self._copy_if_missing(self.source_root / "assets" / "global_mem_insight_template.txt", self.l1_path, l1_seed)
        self._copy_if_missing(self.source_root / "memory" / "global_mem.txt", self.l2_path, "## [FACTS]\n")
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
        return path.read_text(encoding="utf-8") if path.exists() else default_value

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
            if not path.exists():
                continue
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
        rows = payload if isinstance(payload, list) else payload.get("skills", []) if isinstance(payload, dict) else []
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            path = str(row.get("path") or "").strip()
            if name and path:
                normalized.append(row)
        return normalized

    def should_inject_session_recall(self, query: str) -> bool:
        lowered = (query or "").lower()
        return any(term in lowered for term in self.SESSION_RECALL_TRIGGER_TERMS)

    def _index_l3_skills(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        records: list[MemoryRecord] = []
        for entry in self.skill_manifest:
            payload = self._build_skill_payload(entry)
            if not payload:
                continue
            memory_id = hashlib.sha1(f"skill:{entry.get('name')}:{payload}".encode("utf-8")).hexdigest()
            records.append(
                MemoryRecord(
                    memory_id=memory_id,
                    layer="L3",
                    memory_type=MemoryType.PROCEDURE,
                    scope=MemoryScope.GLOBAL,
                    content=payload,
                    evidence="tool:file_read",
                    evidence_ref=f"skill:{entry.get('name')}",
                    verified=True,
                    confidence=0.7,
                    dedupe_key=self._default_dedupe_key(payload),
                    session_id=self.SKILL_INDEX_SESSION_ID,
                    source=f"skill_bootstrap:{entry.get('name', 'unknown')}",
                    created_at=now,
                    updated_at=now,
                )
            )
        self.repository.upsert_many(records)
        if records:
            self.index.upsert(records)

    def _build_skill_payload(self, entry: dict[str, Any]) -> str:
        raw = self._load_skill_raw(entry).strip()
        if not raw:
            return ""
        metadata, body = self._parse_skill_markdown(raw)
        skill = str(entry.get("name") or metadata.get("key") or "").strip()
        if not skill:
            return ""
        summary = str(entry.get("summary") or "").strip() or metadata.get("one_line_summary") or metadata.get("description") or "skill summary unavailable"
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
        candidates = [path] if path.is_absolute() else [self.workspace / path, self.source_root / "memory" / path, self.l3_dir / path]
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
        frontmatter, body = parts[1], parts[2].strip()
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
        return " ".join(line.strip() for line in match.group(1).splitlines() if line.strip())[:320]

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
            return ", ".join(str(item).strip() for item in value if str(item).strip())
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
        return self._merge_skill_blocks(session_skills, self._merge_skill_blocks(*global_blocks))

    @staticmethod
    def _default_dedupe_key(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.lower().strip())
        return re.sub(r"[^a-z0-9\u4e00-\u9fff/._ -]+", "", normalized)

    def query_memory_records(
        self,
        *,
        session_id: str,
        query: str,
        layers: list[str],
        project_id: str = "",
        limit: int | None = None,
    ) -> list[MemoryRecord]:
        include_scopes = ["session", "project", "user", "global"]
        if layers == ["L3"] and session_id != self.SKILL_INDEX_SESSION_ID:
            include_scopes = ["session", "project", "user"]
        filters = QueryFilters(layers=layers, session_id=session_id, project_id=project_id, include_scopes=include_scopes)
        return self.query_service.query(query=query, filters=filters, limit=limit or self.top_k)

    def query_memory(self, session_id: str, query: str, layers: list[str]) -> str:
        rows = self.query_memory_records(session_id=session_id, query=query, layers=layers, limit=self.top_k)
        return "\n".join(f"[{row.layer}] {row.content}" for row in rows) if rows else "(empty)"

    def query_memory_text(self, session_id: str, query: str, layers: list[str]) -> str:
        return self.query_memory(session_id=session_id, query=query, layers=layers)

    def _query_scored_layers(
        self,
        *,
        session_id: str,
        query: str,
        project_id: str,
        task_type: str,
        include_l4: bool,
    ) -> tuple[dict[str, list[ScoredMemory]], list[DroppedMemoryCandidate], dict[str, int]]:
        filters = QueryFilters(layers=["L1", "L2", "L3", "L4"], session_id=session_id, project_id=project_id)
        records_by_layer = self.query_service.query_by_layers(query=query, filters=filters, limit_per_layer=self.top_k)
        records_by_layer["L3"] = [
            *records_by_layer.get("L3", []),
            *self.query_memory_records(
                session_id=self.SKILL_INDEX_SESSION_ID,
                query=query,
                layers=["L3"],
                project_id=project_id,
                limit=self.top_k,
            ),
        ]
        scorer = MemoryScorer()
        scored: dict[str, list[ScoredMemory]] = {}
        dropped: list[DroppedMemoryCandidate] = []
        stats = {"raw_candidates": 0, "kept_candidates": 0, "dropped_candidates": 0}
        for layer, rows in records_by_layer.items():
            ranked = scorer.score(
                query=query,
                candidates=rows,
                task_type=task_type,
                current_session_id=session_id,
                current_project_id=project_id,
            )
            stats["raw_candidates"] += len(ranked)
            kept, layer_dropped = self._apply_retrieval_filters(layer=layer, items=ranked, include_l4=include_l4)
            stats["kept_candidates"] += len(kept)
            stats["dropped_candidates"] += len(layer_dropped)
            scored[layer] = kept
            dropped.extend(layer_dropped)
        return scored, dropped, stats

    @staticmethod
    def _apply_retrieval_filters(
        *,
        layer: str,
        items: list[ScoredMemory],
        include_l4: bool,
    ) -> tuple[list[ScoredMemory], list[DroppedMemoryCandidate]]:
        kept: list[ScoredMemory] = []
        dropped: list[DroppedMemoryCandidate] = []
        for item in items:
            if layer == "L4" and not include_l4:
                dropped.append(DroppedMemoryCandidate(memory_id=item.memory_id, layer=layer, reason="continuity_not_required"))
                continue
            if layer in {"L2", "L3"} and not item.verified:
                dropped.append(DroppedMemoryCandidate(memory_id=item.memory_id, layer=layer, reason="unverified_filtered"))
                continue
            kept.append(item)
        return kept, dropped

    @staticmethod
    def _semantic_compress_layer(items: list[ScoredMemory], max_items: int) -> list[ScoredMemory]:
        compressed: list[ScoredMemory] = []
        seen: set[str] = set()
        for row in items:
            normalized = re.sub(r"\s+", " ", row.text.lower().strip())
            key = normalized[:180]
            if not normalized or key in seen:
                continue
            seen.add(key)
            compressed.append(
                ScoredMemory(
                    layer=row.layer,
                    text=row.text.strip(),
                    memory_id=row.memory_id,
                    evidence=row.evidence,
                    source=row.source,
                    verified=row.verified,
                    score=row.score,
                    recency=row.recency,
                    scope=row.scope,
                    session_id=row.session_id,
                    project_id=row.project_id,
                    updated_at=row.updated_at,
                )
            )
            if len(compressed) >= max_items:
                break
        return compressed

    def _semantic_compress(self, scored_by_layer: dict[str, list[ScoredMemory]]) -> dict[str, list[ScoredMemory]]:
        return {
            "L1": self._semantic_compress_layer(scored_by_layer.get("L1", []), max_items=self.top_k),
            "L2": self._semantic_compress_layer(scored_by_layer.get("L2", []), max_items=self.top_k),
            "L3": self._semantic_compress_layer(scored_by_layer.get("L3", []), max_items=self.top_k),
            "L4": self._semantic_compress_layer(scored_by_layer.get("L4", []), max_items=self.top_k),
        }

    def _build_retrieval_result(
        self,
        *,
        session_id: str,
        project_id: str,
        query: str,
        task_type: str,
        scored_by_layer: dict[str, list[ScoredMemory]],
        dropped: list[DroppedMemoryCandidate],
        stats: dict[str, int],
    ) -> MemoryRetrievalResult:
        candidates = [row for layer in ("L1", "L2", "L3", "L4") for row in scored_by_layer.get(layer, [])]
        return MemoryRetrievalResult(
            session_id=session_id,
            project_id=project_id,
            query=query,
            task_type=task_type,
            candidates=candidates,
            dropped_candidates=dropped,
            retrieval_stats=stats,
        )

    @staticmethod
    def _contains_continuity_terms(query: str) -> bool:
        lowered = (query or "").lower()
        terms = ("continue", "continuity", "previous", "last session", "session", "history", "l4")
        return any(term in lowered for term in terms)

    def _build_pack_features(
        self,
        *,
        facts: list[str],
        procedures: list[str],
        continuity: list[str],
        citations: list[dict[str, str]],
        retrieval: MemoryRetrievalResult,
    ) -> tuple[dict[str, int | float | bool], dict[str, str | bool | float]]:
        total_chars = sum(len(item) for item in [*facts, *procedures, *continuity])
        total_items = len(facts) + len(procedures) + len(continuity)
        estimated_tokens = max(total_chars // 4, 1) if total_chars else 0
        verified = sum(1 for row in retrieval.candidates if row.verified)
        verified_ratio = float(verified) / float(max(len(retrieval.candidates), 1))
        continuity_chars = sum(len(item) for item in continuity)
        factual_chars = sum(len(item) for item in facts)
        citation_density = float(len(citations)) / float(max(total_items, 1))
        features: dict[str, int | float | bool] = {
            "estimated_tokens": estimated_tokens,
            "verified_ratio": round(verified_ratio, 4),
            "continuity_weight": round(float(continuity_chars) / float(max(total_chars, 1)), 4),
            "factuality_weight": round(float(factual_chars) / float(max(total_chars, 1)), 4),
            "tool_relevance": 1.0 if any("tool" in item.lower() for item in procedures) else 0.0,
            "context_span": total_items,
            "contains_l4": bool(continuity),
            "citation_density": round(citation_density, 4),
        }
        strength = "high" if verified_ratio >= 0.75 else ("medium" if verified_ratio >= 0.4 else "low")
        risk_level = "high" if (verified_ratio < 0.4 or citation_density < 0.2) else ("medium" if verified_ratio < 0.75 else "low")
        risk: dict[str, str | bool | float] = {
            "has_unverified": verified < len(retrieval.candidates),
            "has_session_derived": bool(continuity),
            "has_conflicts": False,
            "staleness_level": "low",
            "grounding_strength": strength,
            "risk_level": risk_level,
        }
        return features, risk

    @staticmethod
    def _render_section_text(items: list[str]) -> str:
        rows = [str(item).strip() for item in items if str(item).strip()]
        return "\n".join(rows) if rows else "(empty)"

    def _legacy_layers_from_sections(
        self,
        *,
        facts: list[str],
        procedures: list[str],
        continuity: list[str],
        constraints: list[str],
    ) -> dict[str, str]:
        l1 = self._render_section_text(constraints)
        l2 = self._render_section_text(facts)
        l3 = self._render_section_text(procedures)
        l4 = self._render_section_text(continuity)
        # Deprecated legacy layer fields; retained for compatibility only.
        return {
            "l1": l1,
            "l2": l2,
            "l3": l3,
            "l4": l4,
        }

    def build_memory_pack(self, session_id: str, query: str, project_id: str = "") -> MemoryPack:
        task_type = self.selector.classify_task(query)
        include_l4 = task_type in {"debug", "planning"} or self._contains_continuity_terms(query)
        scored_by_layer, dropped, stats = self._query_scored_layers(
            session_id=session_id,
            query=query,
            project_id=project_id,
            task_type=task_type,
            include_l4=include_l4,
        )
        compressed = self._semantic_compress(scored_by_layer)
        selected_by_layer = compressed
        l0_text = "\n".join(self.l0_rules.splitlines()[:12]).strip()
        selected_items = [row for layer in ("L1", "L2", "L3", "L4") for row in selected_by_layer.get(layer, [])]
        citations = self._ensure_citations(self._build_pack_citations_from_scored(items=selected_items), query)
        facts = [row.text for row in selected_by_layer.get("L2", [])]
        procedures = [row.text for row in selected_by_layer.get("L3", [])]
        continuity = [row.text for row in selected_by_layer.get("L4", [])]
        constraints = [row.text for row in selected_by_layer.get("L1", [])]
        legacy_layers = self._legacy_layers_from_sections(
            facts=facts,
            procedures=procedures,
            continuity=continuity,
            constraints=constraints,
        )
        retrieval = self._build_retrieval_result(
            session_id=session_id,
            project_id=project_id,
            query=query,
            task_type=task_type,
            scored_by_layer=compressed,
            dropped=dropped,
            stats=stats,
        )
        features, risk = self._build_pack_features(
            facts=facts,
            procedures=procedures,
            continuity=continuity,
            citations=citations,
            retrieval=retrieval,
        )
        return MemoryPack(
            task_type=task_type,
            budget=self.selector.budget_for_task(task_type),
            l0=l0_text,
            l1=legacy_layers["l1"],
            l2=legacy_layers["l2"],
            l3=legacy_layers["l3"],
            l4=legacy_layers["l4"],
            citations=citations,
            selected_ids=[row.memory_id for row in selected_items if row.memory_id][: self.top_k * 4],
            facts=facts,
            procedures=procedures,
            continuity=continuity,
            constraints=constraints,
            risk_profile=risk,
            pack_features=features,
            estimated_tokens=int(features.get("estimated_tokens") or 0),
            retrieval_trace={
                "raw_candidates": stats["raw_candidates"],
                "kept_candidates": stats["kept_candidates"],
                "dropped_candidates": stats["dropped_candidates"],
                "dropped_reasons": [row.reason for row in dropped[:12]],
            },
            assembly_trace={
                "facts_count": len(compressed.get("L2", [])),
                "procedures_count": len(compressed.get("L3", [])),
                "continuity_count": len(compressed.get("L4", [])),
                "constraints_count": len(compressed.get("L1", [])),
            },
        )

    @staticmethod
    def _build_pack_citations(*, records: list[MemoryRecord], max_items: int = 6) -> list[dict[str, str]]:
        citations: list[dict[str, str]] = []
        for row in records:
            if not row.content.strip():
                continue
            citation = MemoryCitation(
                memory_id=row.memory_id,
                layer=row.layer,
                snippet=row.content[:180],
                evidence_type=row.evidence_type,
                evidence_ref=row.evidence_ref,
                source=row.source,
            )
            citations.append(
                {
                    "memory_ref": citation.memory_id,
                    "layer": citation.layer,
                    "snippet": citation.snippet,
                    "source_type": "memory",
                }
            )
            if len(citations) >= max_items:
                break
        return citations

    @staticmethod
    def _build_pack_citations_from_scored(*, items: list[ScoredMemory], max_items: int = 6) -> list[dict[str, str]]:
        citations: list[dict[str, str]] = []
        for row in items:
            text = (row.text or "").strip()
            if not text:
                continue
            citations.append(
                {
                    "memory_ref": row.memory_id or f"{row.layer}:{hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]}",
                    "layer": row.layer,
                    "snippet": text[:180],
                    "source_type": "memory",
                }
            )
            if len(citations) >= max_items:
                break
        return citations

    @staticmethod
    def _ensure_citations(citations: list[dict[str, str]], query: str) -> list[dict[str, str]]:
        if citations:
            return citations
        text = (query or "").strip() or "user_query"
        return [
            {
                "memory_ref": f"request:{hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]}",
                "layer": "REQ",
                "snippet": text[:180],
                "source_type": "request_query",
            }
        ]

    @staticmethod
    def _provider_char_budget(provider_style: str) -> int:
        if provider_style == "anthropic_messages":
            return 3000
        return 2200

    @staticmethod
    def _block_priority(section: str) -> int:
        # lower means higher retention priority
        priorities = {"constraints": 0, "facts": 1, "procedures": 2, "continuity": 3}
        return priorities.get(section, 9)

    @staticmethod
    def _build_render_blocks(pack: MemoryPack) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []

        def add(section: str, rows: list[str]) -> None:
            for idx, text in enumerate(rows):
                normalized = str(text).strip()
                if not normalized:
                    continue
                item_id = f"{section}:{idx}:{hashlib.sha1(normalized.encode('utf-8')).hexdigest()[:10]}"
                citation_ids = [
                    str(row.get("memory_ref"))
                    for row in (pack.citations or [])
                    if str(row.get("snippet") or "").strip() and str(row.get("snippet") or "")[:32] in normalized
                ]
                blocks.append(
                    {
                        "section": section,
                        "item_id": item_id,
                        "citation_ids": citation_ids,
                        "priority": MemoryManager._block_priority(section),
                        "text": normalized,
                    }
                )

        add("constraints", list(pack.constraints or []))
        add("facts", list(pack.facts or []))
        add("procedures", list(pack.procedures or []))
        add("continuity", list(pack.continuity or []))
        return blocks

    @staticmethod
    def _render_sections_from_blocks(blocks: list[dict[str, Any]]) -> dict[str, str]:
        grouped: dict[str, list[str]] = {"constraints": [], "facts": [], "procedures": [], "continuity": []}
        for block in blocks:
            section = str(block.get("section") or "")
            text = str(block.get("text") or "").strip()
            if section in grouped and text:
                grouped[section].append(text)
        return {
            "constraints": "\n".join(grouped["constraints"]) if grouped["constraints"] else "(empty)",
            "facts": "\n".join(grouped["facts"]) if grouped["facts"] else "(empty)",
            "procedures": "\n".join(grouped["procedures"]) if grouped["procedures"] else "(empty)",
            "continuity": "\n".join(grouped["continuity"]) if grouped["continuity"] else "(empty)",
        }

    @staticmethod
    def _trim_candidate_index(blocks: list[dict[str, Any]]) -> int | None:
        if not blocks:
            return None
        # drop the lowest-priority block, biasing to the last block for stable progressive trimming
        ordered = sorted(
            range(len(blocks)),
            key=lambda i: (int(blocks[i].get("priority", 9)), i),
            reverse=True,
        )
        return ordered[0] if ordered else None

    @staticmethod
    def _apply_provider_trim(
        *,
        blocks: list[dict[str, Any]],
        max_chars: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        kept = [dict(row) for row in blocks]
        dropped: list[dict[str, Any]] = []

        def total_chars(rows: list[dict[str, Any]]) -> int:
            return sum(len(str(item.get("text") or "")) for item in rows)

        before_chars = total_chars(kept)
        before_tokens = before_chars // 4
        trim_passes = 0
        while kept and total_chars(kept) > max_chars:
            idx = MemoryManager._trim_candidate_index(kept)
            if idx is None:
                break
            candidate = kept.pop(idx)
            candidate["drop_reason"] = "budget_trim_priority"
            dropped.append(candidate)
            trim_passes += 1

        after_chars = total_chars(kept)
        after_tokens = after_chars // 4
        sections_after = MemoryManager._render_sections_from_blocks(kept)
        dropped_by_section = {"facts": 0, "procedures": 0, "continuity": 0, "constraints": 0}
        for row in dropped:
            section = str(row.get("section") or "")
            if section in dropped_by_section:
                dropped_by_section[section] += len(str(row.get("text") or ""))

        report: dict[str, Any] = {
            "mode": "provider_aware_trim",
            "final_render_strategy": "block_oriented_priority_trim",
            "budget_before": max_chars,
            "budget_after": max_chars,
            "estimated_tokens_before": before_tokens,
            "estimated_tokens_after": after_tokens,
            "trimmed_total_chars": before_chars - after_chars,
            "final_total_chars": after_chars,
            "trim_passes": trim_passes,
            "dropped_blocks": [str(row.get("item_id") or "") for row in dropped],
            "dropped_block_ids": [str(row.get("item_id") or "") for row in dropped],
            "drop_reason_by_block": {str(row.get("item_id") or ""): str(row.get("drop_reason") or "") for row in dropped},
            "drop_reasons": [str(row.get("drop_reason") or "") for row in dropped],
            "rendered_block_order": [str(row.get("item_id") or "") for row in kept],
            "retained_counts_by_section": {
                "facts": len([row for row in kept if row.get("section") == "facts"]),
                "procedures": len([row for row in kept if row.get("section") == "procedures"]),
                "continuity": len([row for row in kept if row.get("section") == "continuity"]),
                "constraints": len([row for row in kept if row.get("section") == "constraints"]),
            },
            "retained_fact_ids": [str(row.get("item_id") or "") for row in kept if row.get("section") == "facts"],
            "retained_procedure_ids": [str(row.get("item_id") or "") for row in kept if row.get("section") == "procedures"],
            "retained_continuity_ids": [str(row.get("item_id") or "") for row in kept if row.get("section") == "continuity"],
            "retained_constraint_ids": [str(row.get("item_id") or "") for row in kept if row.get("section") == "constraints"],
            # compatibility fields used by existing tests
            "trimmed_l1_chars": dropped_by_section["constraints"],
            "trimmed_l2_chars": dropped_by_section["facts"],
            "trimmed_l3_chars": dropped_by_section["procedures"],
            "trimmed_l4_chars": dropped_by_section["continuity"],
            "sections_after": sections_after,
        }
        return kept, report

    @staticmethod
    def build_memory_system_blocks(pack: MemoryPack, provider_style: str = "openai") -> list[dict[str, str]]:
        max_chars = MemoryManager._provider_char_budget(provider_style)
        render_blocks = MemoryManager._build_render_blocks(pack)
        kept_blocks, report = MemoryManager._apply_provider_trim(blocks=render_blocks, max_chars=max_chars)
        pack.trim_report = report
        sections = MemoryManager._render_sections_from_blocks(kept_blocks)
        if provider_style == "anthropic_messages":
            return [
                {"category": "memory_l0", "content": pack.l0},
                {"category": "memory_constraints", "content": f"<anthropic_memory_index>\n{sections['constraints']}\n</anthropic_memory_index>"},
                {"category": "memory_procedures", "content": f"<anthropic_relevant_skills>\n{sections['procedures']}\n</anthropic_relevant_skills>"},
                {"category": "memory_continuity", "content": f"<anthropic_session_recall_hints>\n{sections['continuity']}\n</anthropic_session_recall_hints>"},
                {"category": "memory_facts", "content": f"<anthropic_relevant_memory>\n{sections['facts']}\n</anthropic_relevant_memory>"},
            ]
        return [
            {"category": "memory_l0", "content": pack.l0},
            {"category": "memory_constraints", "content": f"<memory_index>\n{sections['constraints']}\n</memory_index>"},
            {"category": "memory_procedures", "content": f"<relevant_skills>\n{sections['procedures']}\n</relevant_skills>"},
            {"category": "memory_continuity", "content": f"<session_recall_hints>\n{sections['continuity']}\n</session_recall_hints>"},
            {"category": "memory_facts", "content": f"<relevant_memory>\n{sections['facts']}\n</relevant_memory>"},
        ]

    @staticmethod
    def render_memory_for_provider(pack: MemoryPack, provider_style: str = "openai") -> str:
        rows = MemoryManager.build_memory_system_blocks(pack=pack, provider_style=provider_style)
        return "\n\n".join(str(row.get("content") or "").strip() for row in rows if str(row.get("content") or "").strip())

    def build_memory_header(self, session_id: str, query: str) -> str:
        return self.render_memory_for_provider(pack=self.build_memory_pack(session_id=session_id, query=query), provider_style="openai")

    def build_memory_system_prompt(self, session_id: str, query: str) -> str:
        return self.build_memory_header(session_id=session_id, query=query)

    def get_memory(self, session_id: str, query: str) -> str:
        return self.build_memory_header(session_id=session_id, query=query)

    def enrich_from_normalized_request(
        self,
        normalized_req: Any,
        provider_style: str = "openai",
        memory_pack: MemoryPack | None = None,
    ) -> tuple[list[dict[str, Any]], MemoryPack]:
        normalized_messages = self._normalize_message_rows(getattr(normalized_req, "messages", []))
        if not self.enabled:
            return normalized_messages, MemoryPack("chat", {}, "", "(empty)", "(empty)", "(empty)", "(empty)", [], [])
        session_id = str(getattr(normalized_req, "session_id", "") or "default")
        query = str(getattr(normalized_req, "user_text", "") or "").strip() or self._extract_latest_user_query(normalized_messages)
        resolved_pack = memory_pack or self.build_memory_pack(session_id=session_id, query=query)
        memory_header = self.render_memory_for_provider(resolved_pack, provider_style=provider_style)
        memory_msg = {"role": "system", "content": f"<nexus_context>\n{memory_header}\n</nexus_context>"}
        return [memory_msg, *normalized_messages], resolved_pack

    def enrich_messages(
        self,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None,
        *,
        session_id: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            return messages
        resolved_session_id = session_id or str((metadata or {}).get("session_id") or "default")
        resolved_query = query or (metadata or {}).get("query") or self._extract_latest_user_query(messages)
        memory_header = self.build_memory_system_prompt(session_id=resolved_session_id, query=resolved_query)
        memory_msg = {"role": "system", "content": f"<nexus_context>\n{memory_header}\n</nexus_context>"}
        return [memory_msg, *messages]

    @staticmethod
    def _normalize_message_rows(messages: list[Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for message in messages:
            if hasattr(message, "model_dump"):
                rows.append(message.model_dump(exclude_none=True))
            elif isinstance(message, dict):
                rows.append(dict(message))
            else:
                rows.append({"role": "user", "content": str(message)})
        return rows

    @staticmethod
    def _extract_latest_user_query(messages: list[dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
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

    def upsert_memory(
        self,
        layer: str | None = None,
        session_id: str | None = None,
        text: str | None = None,
        evidence: str | None = None,
        source: str = "manual",
        *,
        pending: PendingMemoryRecord | None = None,
    ) -> bool:
        if pending is None:
            pending = PendingMemoryRecord(
                layer=layer or "L4",
                memory_type=MemoryType.SESSION_SUMMARY if (layer or "").upper() == "L4" else MemoryType.STABLE_FACT,
                scope=MemoryScope.SESSION if (layer or "").upper() != "L1" else MemoryScope.GLOBAL,
                content=text or "",
                evidence=evidence or "",
                evidence_ref=f"legacy:{layer or 'L4'}",
                verified=(layer or "").upper() in {"L1", "L2", "L3"},
                session_id=session_id or "",
                source=source,
                dedupe_key=self._default_dedupe_key(text or ""),
            )
        result = self.write_policy.validate_pending(pending)
        if not result.accepted:
            return False
        now = datetime.now(timezone.utc).isoformat()
        memory_id = hashlib.sha1(
            "|".join(
                [
                    pending.session_id,
                    result.normalized_layer,
                    (pending.memory_type or "unknown").strip().lower(),
                    result.normalized_scope,
                    pending.dedupe_key or self._default_dedupe_key(result.normalized_content),
                ]
            ).encode("utf-8")
        ).hexdigest()
        row = MemoryRecord(
            memory_id=memory_id,
            layer=result.normalized_layer,
            memory_type=pending.memory_type or MemoryType.SESSION_SUMMARY,
            scope=result.normalized_scope,
            content=result.normalized_content,
            evidence=pending.evidence,
            evidence_ref=pending.evidence_ref,
            evidence_type=pending.evidence_type or self.write_policy.infer_evidence_type(pending.evidence),
            verified=pending.verified,
            confidence=pending.confidence,
            dedupe_key=pending.dedupe_key or self._default_dedupe_key(result.normalized_content),
            session_id=pending.session_id,
            project_id=pending.project_id,
            source=pending.source or source,
            tags=list(pending.tags),
            created_at=now,
            updated_at=now,
            last_accessed_at=now,
        )
        self.repository.upsert(row)
        try:
            self.index.upsert([row])
            self.event_logger.append(
                MemoryEvent(
                    event_type="index_sync_completed",
                    memory_id=row.memory_id,
                    session_id=row.session_id,
                    layer=row.layer,
                    status="completed",
                )
            )
        except Exception as exc:
            self.event_logger.append(
                MemoryEvent(
                    event_type="index_sync_failed",
                    memory_id=row.memory_id,
                    session_id=row.session_id,
                    layer=row.layer,
                    status="failed",
                    payload={"error": str(exc)},
                )
            )
        self._sync_files(layer=row.layer, text=row.content)
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
        rows: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            text = text.replace("\n", " ").strip()
            if role == "user":
                rows.append(f"[USER] {text[:240]}")
            elif role == "assistant":
                rows.append(f"[Agent] {text[:240]}")
        return rows

    def archive_raw_session(self, messages: list[dict[str, Any]]) -> str:
        return "\n".join(self.extract_key_history(messages))

    def archive_session(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        final_result: str = "",
        project_id: str = "",
    ) -> None:
        summary = self.summarizer.build_session_summary(session_id=session_id, messages=messages, final_result=final_result)
        if not summary:
            return
        pending = PendingMemoryRecord(
            layer="L4",
            memory_type=MemoryType.SESSION_SUMMARY,
            scope=MemoryScope.SESSION,
            content=summary,
            evidence="tool:archive_success",
            evidence_ref=f"session:{session_id}",
            verified=False,
            session_id=session_id,
            project_id=project_id,
            source="session_summary",
            dedupe_key=self._default_dedupe_key(summary),
        )
        if self.upsert_memory(pending=pending):
            memory_id = hashlib.sha1(f"{session_id}:{pending.dedupe_key}:L4".encode("utf-8")).hexdigest()
            self._append_l4_archive(session_id=session_id, memory_id=memory_id, summary=summary)
            self.event_logger.append(
                MemoryEvent(event_type="session_archived", memory_id=memory_id, session_id=session_id, layer="L4", status="completed")
            )

    def distill_to_l4(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        self.archive_session(session_id=session_id, messages=messages)

    def start_memory_update(self, session_id: str, messages: list[dict[str, Any]], final_result: str) -> None:
        if not self.enabled:
            return
        self.archive_session(session_id=session_id, messages=messages, final_result=final_result)
        candidates = self._extract_memory_candidates(session_id=session_id, messages=messages, final_result=final_result)
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
        if not self._looks_successful(final_result):
            return candidates
        for fact in self.summarizer.extract_fact_candidates(session_id=session_id, messages=messages, final_result=final_result):
            candidates.append(
                MemoryCandidate(
                    session_id=fact.session_id,
                    suggested_layer=fact.layer,
                    kind="fact_candidate",
                    memory_type=fact.memory_type,
                    scope=fact.scope,
                    project_id=fact.project_id,
                    content=fact.content,
                    evidence=fact.evidence,
                    evidence_ref=fact.evidence_ref,
                    source=fact.source,
                    verified=fact.verified,
                    dedupe_key=fact.dedupe_key,
                    confidence=fact.confidence,
                    created_at=now,
                )
            )
        takeaway = self.summarizer.build_task_takeaway(session_id=session_id, messages=messages, final_result=final_result)
        if takeaway is not None:
            candidates.append(
                MemoryCandidate(
                    session_id=takeaway.session_id,
                    suggested_layer=takeaway.layer,
                    kind="task_takeaway",
                    memory_type=takeaway.memory_type,
                    scope=takeaway.scope,
                    project_id=takeaway.project_id,
                    content=takeaway.content,
                    evidence=takeaway.evidence,
                    evidence_ref=takeaway.evidence_ref,
                    source=takeaway.source,
                    verified=takeaway.verified,
                    dedupe_key=takeaway.dedupe_key,
                    confidence=takeaway.confidence,
                    created_at=now,
                )
            )
        pointer = self.summarizer.build_l1_pointer()
        if pointer is not None:
            candidates.append(
                MemoryCandidate(
                    session_id=session_id,
                    suggested_layer=pointer.layer,
                    kind="index_pointer",
                    memory_type=pointer.memory_type,
                    scope=pointer.scope,
                    content=pointer.content,
                    evidence=pointer.evidence,
                    evidence_ref=pointer.evidence_ref,
                    source=pointer.source,
                    verified=pointer.verified,
                    dedupe_key=pointer.dedupe_key,
                    confidence=pointer.confidence,
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
        seen_dedupe: dict[tuple[str, str, str], str] = {}
        for key, value in states.items():
            dedupe_key = str(value.get("dedupe_key") or "")
            layer = str(value.get("suggested_layer") or "").upper()
            scope = str(value.get("scope") or MemoryScope.SESSION)
            if dedupe_key and layer:
                seen_dedupe[(layer, scope, dedupe_key)] = key
        for row in candidates:
            row.candidate_id = self._candidate_id(row)
            dedupe_key = row.dedupe_key or self._default_dedupe_key(row.content)
            slot = (row.suggested_layer.upper(), row.scope or MemoryScope.SESSION, dedupe_key)
            existing_id = seen_dedupe.get(slot)
            if existing_id:
                existing = states.get(existing_id, {})
                existing_conf = float(existing.get("confidence") or 0.0)
                if existing_conf >= row.confidence:
                    continue
                states.pop(existing_id, None)
            row.dedupe_key = dedupe_key
            row.status = "pending"
            row.updated_at = now
            row.created_at = row.created_at or now
            states[row.candidate_id] = asdict(row)
            seen_dedupe[slot] = row.candidate_id
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
            validation = self.write_policy.validate_candidate(row)
            if not validation.accepted:
                row.status = "rejected"
                row.rejected_reason = "validation_failed"
                row.updated_at = now
                row.index_status = "pending"
                states[row.candidate_id] = asdict(row)
                self.event_logger.append(
                    MemoryEvent(
                        event_type="candidate_rejected",
                        candidate_id=row.candidate_id,
                        session_id=row.session_id,
                        layer=row.suggested_layer,
                        status="rejected",
                        payload={"reason": row.rejected_reason},
                    )
                )
                finished.append(row)
                continue
            pending = PendingMemoryRecord(
                layer=row.suggested_layer,
                memory_type=row.memory_type or row.kind or "unknown",
                scope=row.scope,
                content=row.content,
                evidence=row.evidence,
                evidence_ref=row.evidence_ref,
                evidence_type=row.evidence_type,
                verified=row.verified,
                confidence=row.confidence,
                session_id=row.session_id,
                project_id=row.project_id,
                source=row.source,
                dedupe_key=row.dedupe_key,
            )
            accepted = self.upsert_memory(pending=pending)
            row.status = "committed" if accepted else "rejected"
            row.rejected_reason = "" if accepted else "validation_failed"
            row.updated_at = now
            row.index_status = "completed" if accepted else "pending"
            states[row.candidate_id] = asdict(row)
            self.event_logger.append(
                MemoryEvent(
                    event_type="candidate_committed" if accepted else "candidate_rejected",
                    candidate_id=row.candidate_id,
                    session_id=row.session_id,
                    layer=row.suggested_layer,
                    status=row.status,
                )
            )
            finished.append(row)
        self._save_candidate_states(states)
        self._append_candidate_archive(finished)

    def _candidate_id(self, row: MemoryCandidate) -> str:
        normalized = row.dedupe_key or self._default_dedupe_key(row.content)
        payload = "|".join(
            [
                row.session_id,
                row.suggested_layer.upper(),
                (row.memory_type or row.kind).strip().lower(),
                (row.scope or MemoryScope.SESSION).strip().lower(),
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
        return payload if isinstance(payload, dict) else {}

    def _save_candidate_states(self, states: dict[str, dict[str, Any]]) -> None:
        self.candidates_state_path.write_text(json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_candidate_archive(self, candidates: list[MemoryCandidate]) -> None:
        if not candidates:
            return
        with self.candidates_archive_path.open("a", encoding="utf-8") as handle:
            for row in candidates:
                handle.write(f"{json.dumps(asdict(row), ensure_ascii=False)}\n")

    def _gc_candidate_pool(self, max_states: int = 2000, max_archive_lines: int = 4000) -> None:
        states = self._load_candidate_states()
        if len(states) > max_states:
            ordered = sorted(states.values(), key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
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
        self.candidates_archive_path.write_text("\n".join(lines[-max_archive_lines:]) + "\n", encoding="utf-8")

    @staticmethod
    def _looks_successful(final_result: str) -> bool:
        lowered = final_result.lower()
        if any(token in lowered for token in SUCCESS_NEGATIVE_HINTS):
            return False
        return any(token in lowered for token in SUCCESS_POSITIVE_HINTS)

    def persist_turn(self, request_payload: dict[str, Any], response_payload: dict[str, Any], *, project_id: str = "") -> None:
        metadata = request_payload.get("metadata") or {}
        session_id = str(metadata.get("session_id", "default"))
        messages = request_payload.get("messages") or []
        final_text = self._extract_response_text(response_payload)
        self.start_memory_update(session_id=session_id, messages=messages, final_result=final_text)

    def _append_l4_archive(self, *, session_id: str, memory_id: str, summary: str) -> None:
        row = {
            "session_id": session_id,
            "memory_id": memory_id,
            "summary": summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.l4_archive_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{json.dumps(row, ensure_ascii=False)}\n")

    @staticmethod
    def _extract_response_text(response_payload: dict[str, Any]) -> str:
        try:
            choices = response_payload.get("choices") or []
            message = (choices[0].get("message") or {}) if choices else {}
            content = message.get("content") or ""
            return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        except Exception:
            return ""
