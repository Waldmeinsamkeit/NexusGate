from __future__ import annotations

import copy
import json
from typing import Any

from nexusgate.config import settings
from nexusgate.prompting.system_blocks import (
    build_system_blocks,
    dedupe_and_merge_system_blocks,
    render_system_blocks_for_provider,
)


_RECALL_KEYWORDS = (
    "继续",
    "接着",
    "上次",
    "回忆",
    "之前做到哪",
    "延续",
    "continue",
    "resume",
    "recall",
    "previous",
    "last session",
)
_RECALL_METADATA_KEYS = ("continuation", "needs_session_recall", "resume")
_RECALL_MODES = {"off", "auto", "always"}


def build_memory_management_sop_block() -> str:
    return (
        "<memory_management_sop>\n"
        "1. ONLY use facts from <nexus_context>; treat [unverified] items as hints, not truth.\n"
        "2. When two memories conflict, trust the one with newer timestamp + verified=true.\n"
        "3. Never extend a fact beyond what the evidence literally states.\n"
        "</memory_management_sop>"
    )


def build_session_memory_recall_sop_block() -> str:
    return (
        "<session_memory_recall>\n"
        "Recover: goal, constraints, decisions, completed_work, blockers, next_step.\n"
        "Label each as confirmed/inferred/unknown. Never fabricate missing fields.\n"
        "</session_memory_recall>"
    )


def should_enable_session_memory_recall(user_text: str, metadata: dict[str, Any] | None) -> bool:
    lowered = (user_text or "").lower()
    if any(keyword in lowered for keyword in _RECALL_KEYWORDS):
        return True
    meta = metadata if isinstance(metadata, dict) else {}
    for key in _RECALL_METADATA_KEYS:
        if bool(meta.get(key)):
            return True
    return False


def build_memory_usage_skill_block() -> str:
    return (
        "<memory_usage_skill>\n"
        "1. Check <nexus_context> before acting; on resume/continue requests, summarize recovered state first.\n"
        "2. Items marked [unverified] are hypotheses—never cite them as confirmed.\n"
        "3. If context is insufficient for a safe action, ask one clarification question before proceeding.\n"
        "</memory_usage_skill>"
    )


def build_sop_system_blocks(
    user_text: str,
    metadata: dict[str, Any] | None,
    *,
    has_memory_content: bool = False,
) -> list[str]:
    blocks: list[str] = []
    if settings.enable_memory_management_sop and has_memory_content:
        blocks.append(build_memory_management_sop_block())
        blocks.append(build_memory_usage_skill_block())

    if not settings.enable_session_memory_recall_sop:
        return blocks

    mode = str(settings.session_memory_recall_mode or "auto").strip().lower()
    if mode not in _RECALL_MODES:
        mode = "auto"
    if mode == "always":
        blocks.append(build_session_memory_recall_sop_block())
    elif mode == "auto" and should_enable_session_memory_recall(user_text=user_text, metadata=metadata):
        blocks.append(build_session_memory_recall_sop_block())
    return blocks


def extract_metadata_from_responses_payload(payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("metadata")
    if isinstance(meta, dict):
        return meta
    return {}


def extract_user_text_from_responses_payload(payload: dict[str, Any]) -> str:
    input_value = payload.get("input")
    text = _extract_text_from_input(input_value)
    if text:
        return text
    instructions = payload.get("instructions")
    if isinstance(instructions, str):
        return instructions
    return ""


def build_responses_system_blocks(
    *,
    user_text: str,
    metadata: dict[str, Any] | None,
    memory_context: str | None = None,
) -> list[str]:
    blocks = build_sop_system_blocks(
        user_text=user_text,
        metadata=metadata,
        has_memory_content=bool(str(memory_context or "").strip()),
    )
    memory_text = str(memory_context or "").strip()
    raw_blocks: list[dict[str, Any]] = [
        {
            "category": "sop",
            "content": block,
            "source": "sop",
            "priority": 20,
        }
        for block in blocks
        if str(block or "").strip()
    ]
    if memory_text:
        raw_blocks.append(
            {
                "category": "memory_context",
                "content": memory_text,
                "source": "memory",
                "priority": 30,
                "singleton": True,
            }
        )
    merged = dedupe_and_merge_system_blocks(build_system_blocks(raw_blocks))
    return render_system_blocks_for_provider(merged, provider_style="openai")



def inject_system_blocks_into_responses_payload(
    payload: dict[str, Any],
    *,
    user_text: str,
    metadata: dict[str, Any] | None,
    memory_context: str | None = None,
) -> dict[str, Any]:
    system_blocks = build_responses_system_blocks(
        user_text=user_text,
        metadata=metadata,
        memory_context=memory_context,
    )
    if not system_blocks:
        return dict(payload)

    patched = copy.deepcopy(payload)
    system_text = "\n\n".join(system_blocks).strip()
    if not system_text:
        return patched

    instructions = patched.get("instructions")
    if isinstance(instructions, str) and instructions.strip():
        patched["instructions"] = f"{system_text}\n\n{instructions}"
        return patched

    input_value = patched.get("input")
    system_item = {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    if isinstance(input_value, str):
        patched["input"] = [system_item, {"role": "user", "content": [{"type": "input_text", "text": input_value}]}]
        return patched
    if isinstance(input_value, list):
        patched["input"] = [system_item, *input_value]
        return patched
    if isinstance(input_value, dict):
        if _dict_input_is_textual(input_value):
            patched["input"] = [system_item, input_value]
        return patched
    return patched



def inject_sop_into_responses_payload(
    payload: dict[str, Any],
    *,
    user_text: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    return inject_system_blocks_into_responses_payload(
        payload,
        user_text=user_text,
        metadata=metadata,
        memory_context=None,
    )


def _extract_text_from_input(input_value: Any) -> str:
    if isinstance(input_value, str):
        return input_value
    if isinstance(input_value, list):
        for item in reversed(input_value):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").lower()
            if role not in {"user", "input_user", "message"}:
                continue
            text = _extract_text_from_content(item.get("content"))
            if text:
                return text
        return ""
    if isinstance(input_value, dict):
        for key in ("text", "content"):
            text = _extract_text_from_content(input_value.get(key))
            if text:
                return text
    return ""


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for block in content:
            if isinstance(block, str):
                chunks.append(block)
                continue
            if not isinstance(block, dict):
                chunks.append(str(block))
                continue
            block_type = str(block.get("type") or "")
            if block_type in {"input_text", "output_text", "text"}:
                chunks.append(str(block.get("text") or ""))
            elif "text" in block:
                chunks.append(str(block.get("text") or ""))
            else:
                chunks.append(json.dumps(block, ensure_ascii=False))
        return "\n".join(row for row in chunks if row).strip()
    if isinstance(content, dict):
        if "text" in content:
            return str(content.get("text") or "")
        return json.dumps(content, ensure_ascii=False)
    if content is None:
        return ""
    return str(content)


def _dict_input_is_textual(row: dict[str, Any]) -> bool:
    text = _extract_text_from_input(row)
    return bool(text.strip())
