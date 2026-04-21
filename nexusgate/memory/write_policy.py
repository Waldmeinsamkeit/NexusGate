from __future__ import annotations

from nexusgate.memory.models import MemoryCandidate


class MemoryWritePolicy:
    def require_evidence(self, candidate: MemoryCandidate) -> bool:
        layer = candidate.suggested_layer.upper()
        if layer == "L4":
            return True
        return bool(candidate.evidence.strip() and candidate.evidence_ref.strip())

    def detect_volatility(self, candidate: MemoryCandidate) -> bool:
        text = candidate.content.lower()
        volatile_tokens = ("current time", "timestamp", "pid", "tmp", "temp")
        return any(token in text for token in volatile_tokens)

    def decide_target_layer(self, candidate: MemoryCandidate) -> str:
        if candidate.suggested_layer:
            return candidate.suggested_layer.upper()
        if candidate.memory_type in {"stable_fact"}:
            return "L2"
        if candidate.memory_type in {"procedure", "lesson"}:
            return "L3"
        return "L4"

    def validate_candidate(self, candidate: MemoryCandidate) -> bool:
        layer = self.decide_target_layer(candidate)
        if not candidate.content.strip():
            return False
        if layer in {"L1", "L2", "L3"} and not candidate.verified:
            return False
        if not self.require_evidence(candidate):
            return False
        if layer in {"L1", "L2", "L3"} and self.detect_volatility(candidate):
            return False
        return layer in {"L1", "L2", "L3", "L4"}

