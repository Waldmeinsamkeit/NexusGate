from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MemoryContext:
    enriched_messages: list[dict[str, Any]]
    traces: dict[str, Any]


class BaseMemoryLayer:
    layer = "L?"
    max_item_chars = 240

    def accepts(self, candidate: dict[str, Any]) -> bool:
        return str(candidate.get("suggested_layer", "")).upper() == self.layer

    def normalize(self, candidate: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(candidate)
        content = str(candidate.get("content", "")).strip()
        content = re.sub(r"\s+", " ", content)
        normalized["content"] = content[: self.max_item_chars]
        return normalized

    def enrich(self, query: str, items: list[dict[str, Any]], budget: int) -> str:
        rows: list[str] = []
        remaining = max(budget, 0)
        for item in items:
            if not self.accepts(item):
                continue
            row = str(self.normalize(item).get("content", "")).strip()
            if not row or remaining <= 0:
                continue
            if len(row) > remaining:
                row = row[:remaining]
            rows.append(row)
            remaining -= len(row)
        return "\n".join(rows) if rows else "(empty)"

    def persist(self, request_payload: dict[str, Any], response_payload: dict[str, Any]) -> None:
        return None


class L1Layer(BaseMemoryLayer):
    layer = "L1"
    max_item_chars = 96

    def accepts(self, candidate: dict[str, Any]) -> bool:
        if not super().accepts(candidate):
            return False
        content = str(candidate.get("content", ""))
        return "->" in content


class L2Layer(BaseMemoryLayer):
    layer = "L2"

    def accepts(self, candidate: dict[str, Any]) -> bool:
        return super().accepts(candidate) and bool(candidate.get("verified"))


class L3Layer(BaseMemoryLayer):
    layer = "L3"

    def accepts(self, candidate: dict[str, Any]) -> bool:
        return super().accepts(candidate) and bool(candidate.get("verified"))

    def normalize(self, candidate: dict[str, Any]) -> dict[str, Any]:
        normalized = super().normalize(candidate)
        content = str(normalized.get("content", ""))
        if content and not content.startswith("task_takeaway:"):
            normalized["content"] = f"task_takeaway: {content}"[: self.max_item_chars]
        return normalized


class L4Layer(BaseMemoryLayer):
    layer = "L4"
    max_item_chars = 600


class SessionMemoryLayer(L4Layer):
    pass


class WorkingMemoryLayer(L2Layer):
    pass


class EpisodicMemoryLayer(L3Layer):
    pass


class SemanticMemoryLayer(L1Layer):
    pass


class ArchiveMemoryLayer(L4Layer):
    pass
