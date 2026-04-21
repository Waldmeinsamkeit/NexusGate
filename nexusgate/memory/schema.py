from __future__ import annotations

from dataclasses import dataclass


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
    evidence_type: str
    evidence_ref: str


@dataclass(slots=True)
class MemoryItem:
    memory_id: str
    layer: str
    memory_type: str
    scope: str
    content: str
    evidence: str
    evidence_ref: str
    verified: bool
    confidence: float
    dedupe_key: str
    session_id: str
    source: str

