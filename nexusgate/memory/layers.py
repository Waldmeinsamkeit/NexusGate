from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MemoryContext:
    enriched_messages: list[dict[str, Any]]
    traces: dict[str, Any]


class BaseMemoryLayer:
    name = "base"

    def enrich(self, messages: list[dict[str, Any]], metadata: dict[str, Any]) -> MemoryContext:
        return MemoryContext(enriched_messages=messages, traces={self.name: "noop"})

    def persist(self, request_payload: dict[str, Any], response_payload: dict[str, Any]) -> None:
        return None


class SessionMemoryLayer(BaseMemoryLayer):
    name = "session"


class WorkingMemoryLayer(BaseMemoryLayer):
    name = "working"


class EpisodicMemoryLayer(BaseMemoryLayer):
    name = "episodic"


class SemanticMemoryLayer(BaseMemoryLayer):
    name = "semantic"


class ArchiveMemoryLayer(BaseMemoryLayer):
    name = "archive"

