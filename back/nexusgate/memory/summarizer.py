from __future__ import annotations

import json
import re
from typing import Any

from nexusgate.memory.schema import MemoryScope, MemoryType, PendingMemoryRecord
from nexusgate.memory.write_policy import MemoryWritePolicy


class MemorySummarizer:
    def __init__(self, write_policy: MemoryWritePolicy) -> None:
        self.write_policy = write_policy

    def strip_operational_noise(self, text: str) -> str:
        cleaned = []
        for line in (text or "").splitlines():
            lowered = line.lower()
            if any(token in lowered for token in ("<environment_context>", "<nexus_context>", "agents.md")):
                continue
            cleaned.append(line.strip())
        return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()

    def build_session_summary(
        self,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
        final_result: str,
    ) -> str:
        goal = self._extract_latest_message(messages, "user")[:180] or "unknown"
        action = self._extract_latest_message(messages, "assistant")[:180] or "unknown"
        result = self.strip_operational_noise(final_result)[:220] or "unknown"
        summary = (
            f"[USER] {goal}\n"
            f"[Agent] {action}\n"
            f"[RESULT] {result}\n"
            "未完成/下一步: 根据用户后续请求继续。"
        )
        return self.strip_operational_noise(summary)

    def extract_fact_candidates(
        self,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
        final_result: str,
    ) -> list[PendingMemoryRecord]:
        pool = [final_result, self._extract_latest_message(messages, "assistant")]
        rows: list[PendingMemoryRecord] = []
        seen: set[str] = set()
        patterns = [
            r"(?:file|path)\s+([A-Za-z0-9_./\\-]+)",
            r"(?:port|timeout|retries)\s*(?:is|=)\s*([A-Za-z0-9_.-]+)",
            r"(?:config|env)\s*[:=]\s*([A-Za-z0-9_./\\-]+)",
        ]
        for text in pool:
            for pattern in patterns:
                for match in re.findall(pattern, text or "", flags=re.IGNORECASE):
                    content = f"stable_fact: {match.strip()}"
                    key = self.write_policy.normalize_content(content).lower()
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        PendingMemoryRecord(
                            layer="L2",
                            memory_type=MemoryType.STABLE_FACT,
                            scope=MemoryScope.SESSION,
                            content=content,
                            evidence="tool:success",
                            evidence_ref=f"text_match:{match.strip()}",
                            verified=True,
                            session_id=session_id,
                            source="stable_fact",
                            dedupe_key=key,
                            confidence=0.8,
                        )
                    )
        return rows

    def build_task_takeaway(
        self,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
        final_result: str,
    ) -> PendingMemoryRecord | None:
        latest_user = self._extract_latest_message(messages, "user")
        latest_assistant = self._extract_latest_message(messages, "assistant")
        if not (latest_user or latest_assistant or final_result):
            return None
        content = (
            "task_takeaway: "
            f"goal={latest_user[:80] or 'unknown'}; "
            f"action={latest_assistant[:80] or 'unknown'}; "
            f"result={final_result[:80] or 'unknown'}"
        )
        return PendingMemoryRecord(
            layer="L3",
            memory_type=MemoryType.LESSON,
            scope=MemoryScope.SESSION,
            content=content,
            evidence="tool:success",
            evidence_ref="result:final_summary",
            verified=True,
            session_id=session_id,
            source="task_takeaway",
            dedupe_key=self.write_policy.normalize_content(content).lower(),
            confidence=0.7,
        )

    def build_l1_pointer(self) -> PendingMemoryRecord | None:
        content = "memory_write_rules -> L2; session_recall -> L4; task_takeaway -> L3"
        return PendingMemoryRecord(
            layer="L1",
            memory_type=MemoryType.INDEX_POINTER,
            scope=MemoryScope.GLOBAL,
            content=content,
            evidence="tool:success",
            evidence_ref="policy:memory_write_rules",
            verified=True,
            source="l1_pointer",
            dedupe_key=self.write_policy.normalize_content(content).lower(),
            confidence=0.6,
        )

    @staticmethod
    def _extract_latest_message(messages: list[dict[str, Any]], role: str) -> str:
        for msg in reversed(messages):
            if msg.get("role") != role:
                continue
            content = msg.get("content")
            if isinstance(content, str):
                return content.replace("\n", " ").strip()
            return json.dumps(content, ensure_ascii=False)
        return ""
