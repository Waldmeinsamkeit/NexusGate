from __future__ import annotations

import re

from nexusgate.memory.models import MemoryItem
from nexusgate.memory.policies import EVIDENCE_PRIORITY_HINTS, TASK_LAYER_WEIGHTS


def query_terms(query: str) -> list[str]:
    text = (query or "").lower()
    alpha_terms = re.findall(r"[a-z0-9_/-]{3,}", text)
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    cjk_terms = [chunk[i : i + 2] for chunk in cjk_chunks for i in range(max(len(chunk) - 1, 1))]
    terms = [term for term in [*alpha_terms, *cjk_terms] if term]
    if terms:
        return terms
    return [text.strip()] if text.strip() else []


def score_items(query: str, task_type: str, items: list[MemoryItem]) -> list[MemoryItem]:
    terms = query_terms(query)
    layer_weights = TASK_LAYER_WEIGHTS.get(task_type, TASK_LAYER_WEIGHTS["chat"])
    scored: list[MemoryItem] = []
    for item in items:
        lowered = item.text.lower()
        overlap = sum(1 for term in terms if term and term in lowered)
        evidence_bonus = _evidence_bonus(item)
        score = overlap * 2.0 + layer_weights.get(item.layer, 0.0) * 1.5
        if item.verified:
            score += 2.0
        score += item.recency + evidence_bonus
        scored.append(
            MemoryItem(
                layer=item.layer,
                text=item.text,
                evidence=item.evidence,
                source=item.source,
                verified=item.verified,
                score=score,
                recency=item.recency,
            )
        )
    return scored


def rank_items(items: list[MemoryItem], task_type: str) -> list[MemoryItem]:
    layer_weights = TASK_LAYER_WEIGHTS.get(task_type, TASK_LAYER_WEIGHTS["chat"])
    return sorted(
        items,
        key=lambda item: (
            item.score,
            1 if item.verified else 0,
            layer_weights.get(item.layer, 0.0),
            -len(item.text),
        ),
        reverse=True,
    )


def dedupe_key(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[\s_:]+", " ", lowered)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff/\.\- ]+", "", lowered)


def dedupe_items(items: list[MemoryItem]) -> list[MemoryItem]:
    selected: dict[str, MemoryItem] = {}
    for item in items:
        key = dedupe_key(item.text)
        current = selected.get(key)
        if current is None or _prefer_item(item, current):
            selected[key] = item
    return list(selected.values())


def _evidence_bonus(item: MemoryItem) -> float:
    haystack = f"{item.evidence} {item.source} {item.text}".lower()
    return 0.8 if any(token in haystack for token in EVIDENCE_PRIORITY_HINTS) else 0.0


def _prefer_item(candidate: MemoryItem, existing: MemoryItem) -> bool:
    if candidate.verified != existing.verified:
        return candidate.verified
    if candidate.score != existing.score:
        return candidate.score > existing.score
    if len(candidate.text) != len(existing.text):
        return len(candidate.text) < len(existing.text)
    layer_rank = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
    return layer_rank.get(candidate.layer, 0) > layer_rank.get(existing.layer, 0)
