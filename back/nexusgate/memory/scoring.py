from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from nexusgate.memory.models import ScoredMemory
from nexusgate.memory.policies import SOURCE_RELIABILITY_WEIGHTS, TASK_LAYER_WEIGHTS
from nexusgate.memory.schema import MemoryRecord


def query_terms(query: str) -> list[str]:
    text = (query or "").lower()
    alpha_terms = re.findall(r"[a-z0-9_/-]{2,}", text)
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    cjk_terms = [chunk[i : i + 2] for chunk in cjk_chunks for i in range(max(len(chunk) - 1, 1))]
    terms = [term for term in [*alpha_terms, *cjk_terms] if term]
    return terms or ([text.strip()] if text.strip() else [])


def normalize_text(text: str) -> str:
    lowered = (text or "").lower().strip()
    lowered = re.sub(r"[\s_:]+", " ", lowered)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff/\.\- ]+", "", lowered)


def dedupe_key(record: MemoryRecord | str) -> str:
    if isinstance(record, str):
        return normalize_text(record)
    return normalize_text(record.dedupe_key or record.content)


def scope_bonus(record: MemoryRecord, current_session_id: str, current_project_id: str) -> float:
    if record.scope == "session" and current_session_id and record.session_id == current_session_id:
        return 2.2
    if record.scope == "project" and current_project_id and record.project_id == current_project_id:
        return 1.6
    if record.scope == "user":
        return 1.0
    if record.scope == "global":
        return 0.6
    return 0.0


def recency_score(updated_at: str) -> float:
    if not updated_at:
        return 0.0
    try:
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    now = datetime.now(timezone.utc)
    age_hours = max((now - ts.astimezone(timezone.utc)).total_seconds() / 3600.0, 0.0)
    return max(0.0, 1.2 - math.log1p(age_hours) * 0.25)


def dedupe(records: list[ScoredMemory]) -> list[ScoredMemory]:
    selected: dict[str, ScoredMemory] = {}
    for row in records:
        key = normalize_text(row.text)
        cur = selected.get(key)
        if cur is None or (row.score, row.verified, row.recency) > (cur.score, cur.verified, cur.recency):
            selected[key] = row
    return list(selected.values())


class MemoryScorer:
    def score(
        self,
        *,
        query: str,
        candidates: list[MemoryRecord],
        task_type: str,
        current_session_id: str = "",
        current_project_id: str = "",
    ) -> list[ScoredMemory]:
        terms = query_terms(query)
        layer_weights = TASK_LAYER_WEIGHTS.get(task_type, TASK_LAYER_WEIGHTS["chat"])
        out: list[ScoredMemory] = []
        for row in candidates:
            lowered = row.content.lower()
            overlap = sum(1 for term in terms if term and term in lowered)
            exact = 2.0 if query and query.lower().strip() in lowered else 0.0
            verified_bonus = 1.4 if row.verified else 0.0
            layer_prior = layer_weights.get(row.layer, 0.0) * 1.4
            src_bonus = SOURCE_RELIABILITY_WEIGHTS.get(row.source, 0.8)
            recency = recency_score(row.updated_at or row.created_at)
            score = exact + overlap * 1.8 + verified_bonus + layer_prior + src_bonus + recency
            score += scope_bonus(row, current_session_id=current_session_id, current_project_id=current_project_id)
            out.append(
                ScoredMemory(
                    memory_id=row.memory_id,
                    layer=row.layer,
                    text=row.content,
                    evidence=row.evidence,
                    source=row.source,
                    verified=row.verified,
                    confidence=row.confidence,
                    score=score,
                    recency=recency,
                    scope=row.scope,
                    session_id=row.session_id,
                    project_id=row.project_id,
                    updated_at=row.updated_at,
                )
            )
        ranked = sorted(
            out,
            key=lambda item: (item.score, item.verified, item.recency),
            reverse=True,
        )
        return dedupe(ranked)


def score_items(query: str, task_type: str, items: list[ScoredMemory]) -> list[ScoredMemory]:
    scorer = MemoryScorer()
    records = [
        MemoryRecord(
            memory_id=item.memory_id or hashlib_id(item.layer, item.text),
            layer=item.layer,
            memory_type="legacy",
            scope=item.scope or "session",
            content=item.text,
            evidence=item.evidence,
            verified=item.verified,
            source=item.source,
            session_id=item.session_id,
            project_id=item.project_id,
            updated_at=item.updated_at,
        )
        for item in items
    ]
    return scorer.score(query=query, candidates=records, task_type=task_type)


def dedupe_items(items: list[ScoredMemory]) -> list[ScoredMemory]:
    return dedupe(items)


def hashlib_id(layer: str, text: str) -> str:
    import hashlib

    return hashlib.sha1(f"{layer}:{text}".encode("utf-8")).hexdigest()
