from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class MemoryScope:
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"
    USER = "user"


class MemoryType:
    STABLE_FACT = "stable_fact"
    PROCEDURE = "procedure"
    LESSON = "lesson"
    SESSION_SUMMARY = "session_summary"
    INDEX_POINTER = "index_pointer"


@dataclass(slots=True)
class MemoryCitation:
    memory_id: str
    layer: str
    snippet: str
    evidence_type: str
    evidence_ref: str
    source: str = ""


@dataclass(slots=True)
class MemoryRecord:
    memory_id: str
    layer: str
    memory_type: str
    scope: str
    content: str
    summary: str = ""
    evidence: str = ""
    evidence_ref: str = ""
    evidence_type: str = ""
    verified: bool = False
    confidence: float = 0.0
    dedupe_key: str = ""
    session_id: str = ""
    project_id: str = ""
    source: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    last_accessed_at: str = ""
    archived: bool = False
    supersedes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PendingMemoryRecord:
    layer: str
    memory_type: str
    scope: str
    content: str
    evidence: str
    evidence_ref: str = ""
    evidence_type: str = ""
    verified: bool = False
    confidence: float = 0.0
    session_id: str = ""
    project_id: str = ""
    source: str = ""
    dedupe_key: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class QueryFilters:
    layers: list[str]
    session_id: str = ""
    project_id: str = ""
    include_scopes: list[str] = field(default_factory=list)
    only_verified: bool = False
    exclude_archived: bool = True


# Backward compatibility alias for existing imports.
MemoryItem = MemoryRecord
