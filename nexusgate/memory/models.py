from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MemoryCandidate:
    suggested_layer: str
    content: str
    evidence: str
    source: str
    verified: bool
    session_id: str
    kind: str = ""
    confidence: float = 0.0
    created_at: str = ""


@dataclass(slots=True)
class MemoryItem:
    layer: str
    text: str
    evidence: str = ""
    source: str = ""
    verified: bool = False
    score: float = 0.0
    recency: float = 0.0


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
