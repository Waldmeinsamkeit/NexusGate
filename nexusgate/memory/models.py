from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MemoryCandidate:
    suggested_layer: str
    content: str
    evidence: str
    source: str
    verified: bool
    session_id: str
    kind: str = ""
    memory_type: str = ""
    scope: str = "session"
    project_id: str = ""
    evidence_ref: str = ""
    evidence_type: str = ""
    dedupe_key: str = ""
    confidence: float = 0.0
    created_at: str = ""
    candidate_id: str = ""
    status: str = "pending"
    updated_at: str = ""
    rejected_reason: str = ""
    index_status: str = "pending"
    turn_range: str = ""


@dataclass(slots=True)
class ScoredMemory:
    layer: str
    text: str
    memory_id: str = ""
    evidence: str = ""
    source: str = ""
    verified: bool = False
    score: float = 0.0
    recency: float = 0.0
    scope: str = ""
    session_id: str = ""
    project_id: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class MemoryContext:
    task_type: str
    l0: str
    l1: str
    l2: str
    l3: str
    l4: str


@dataclass(slots=True)
class LayerBudgets:
    l0: int = 300
    l1: int = 600
    l2: int = 1200
    l3: int = 1200
    l4: int = 600


@dataclass(slots=True)
class MemoryPack:
    task_type: str
    budget: dict[str, int]
    l0: str
    l1: str
    l2: str
    l3: str
    l4: str
    citations: list[dict[str, str]]
    selected_ids: list[str]
    facts: list[str] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)
    continuity: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    risk_profile: dict[str, str | bool | float] = field(default_factory=dict)
    pack_features: dict[str, int | float | bool] = field(default_factory=dict)
    estimated_tokens: int = 0
    trim_report: dict[str, int | str] = field(default_factory=dict)
    retrieval_trace: dict[str, object] = field(default_factory=dict)
    assembly_trace: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class DroppedMemoryCandidate:
    memory_id: str
    layer: str
    reason: str


@dataclass(slots=True)
class MemoryRetrievalResult:
    session_id: str
    project_id: str
    query: str
    task_type: str
    candidates: list[ScoredMemory]
    dropped_candidates: list[DroppedMemoryCandidate]
    retrieval_stats: dict[str, int | float]


# Backward compatibility alias for existing scoring/selector tests.
MemoryItem = ScoredMemory
