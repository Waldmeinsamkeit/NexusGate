from __future__ import annotations

import re
from dataclasses import dataclass

from nexusgate.memory.models import MemoryCandidate
from nexusgate.memory.policies import OPERATIONAL_NOISE_HINTS, VOLATILE_HINTS
from nexusgate.memory.schema import PendingMemoryRecord


@dataclass(slots=True)
class ValidationResult:
    accepted: bool
    normalized_content: str
    normalized_layer: str
    normalized_scope: str
    reason: str = ""


class MemoryWritePolicy:
    def validate_pending(self, pending: PendingMemoryRecord) -> ValidationResult:
        content = self.normalize_content(pending.content)
        layer = pending.layer.upper().strip()
        scope = (pending.scope or "session").strip().lower()
        if not content:
            return ValidationResult(False, content, layer, scope, "empty_content")
        if layer not in {"L1", "L2", "L3", "L4"}:
            return ValidationResult(False, content, layer, scope, "invalid_layer")
        if layer in {"L1", "L2", "L3"} and not pending.verified:
            return ValidationResult(False, content, layer, scope, "unverified_high_layer")
        if layer != "L4" and not self.require_evidence(layer, pending.evidence, pending.evidence_ref):
            return ValidationResult(False, content, layer, scope, "missing_evidence")
        if layer in {"L1", "L2", "L3"} and self.detect_volatility(content):
            return ValidationResult(False, content, layer, scope, "volatile_content")
        if self.detect_operational_noise(content) and layer in {"L2", "L3"}:
            return ValidationResult(False, content, layer, scope, "operational_noise")
        if layer == "L4" and not pending.session_id.strip():
            return ValidationResult(False, content, layer, scope, "missing_session")
        return ValidationResult(True, content, layer, scope)

    def validate_candidate(self, candidate: MemoryCandidate) -> ValidationResult:
        pending = PendingMemoryRecord(
            layer=candidate.suggested_layer,
            memory_type=candidate.memory_type or candidate.kind or "",
            scope=candidate.scope,
            content=candidate.content,
            evidence=candidate.evidence,
            evidence_ref=candidate.evidence_ref,
            evidence_type=candidate.evidence_type,
            verified=candidate.verified,
            confidence=candidate.confidence,
            session_id=candidate.session_id,
            project_id=candidate.project_id,
            source=candidate.source,
            dedupe_key=candidate.dedupe_key,
        )
        return self.validate_pending(pending)

    @staticmethod
    def require_evidence(layer: str, evidence: str, evidence_ref: str) -> bool:
        if layer.upper() == "L4":
            return True
        return bool(evidence.strip() and evidence_ref.strip())

    @staticmethod
    def detect_volatility(text: str) -> bool:
        lowered = text.lower()
        return any(token in lowered for token in VOLATILE_HINTS)

    @staticmethod
    def detect_operational_noise(text: str) -> bool:
        lowered = text.lower()
        return any(token in lowered for token in OPERATIONAL_NOISE_HINTS)

    @staticmethod
    def normalize_content(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def infer_evidence_type(evidence: str) -> str:
        lowered = (evidence or "").lower()
        if lowered.startswith("tool:"):
            return "tool"
        if lowered.startswith("file:"):
            return "file"
        if lowered.startswith("result:"):
            return "result"
        return "unknown"
