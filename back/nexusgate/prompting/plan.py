from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nexusgate.prompting.system_blocks import (
    SystemBlock,
    build_system_blocks,
    dedupe_and_merge_system_blocks,
)


@dataclass(slots=True)
class ConversationItem:
    role: str
    content: Any
    name: str | None = None


@dataclass(slots=True)
class ToolContextItem:
    name: str
    arguments: str = ""
    result: str = ""


@dataclass(slots=True)
class CitationItem:
    memory_ref: str
    snippet: str = ""


@dataclass(slots=True)
class NormalizedPromptPlan:
    provider_style: str
    system_blocks: list[SystemBlock] = field(default_factory=list)
    conversation_items: list[ConversationItem] = field(default_factory=list)
    tool_context_items: list[ToolContextItem] = field(default_factory=list)
    citations: list[CitationItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


_LANGUAGE_HINTS: dict[str, str] = {
    "zh": "用户使用中文，请用中文回复。",
    "ja": "ユーザーは日本語を使用しています。日本語で回答してください。",
    "ko": "사용자가 한국어를 사용하고 있습니다. 한국어로 답변해 주세요.",
    "ru": "Пользователь использует русский язык. Отвечайте на русском.",
    "ar": "المستخدم يستخدم العربية. يرجى الرد باللغة العربية.",
    "en": "User is using English. Respond in English.",
}


def build_default_system_blocks(
    *,
    l0_meta_rules: str,
    sop_blocks: list[str],
    grounding_rules: str,
    evidence_blocks: dict[str, str],
    citation_block: str,
    memory_context: str | None = None,
    detected_language: str = "unknown",
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        {"category": "meta_rules", "content": l0_meta_rules, "source": "l0", "priority": 5, "singleton": True},
    ]
    # Language hint — high priority so model sees it early
    lang_hint = _LANGUAGE_HINTS.get(detected_language, "")
    if lang_hint:
        blocks.append({"category": "language_hint", "content": lang_hint, "source": "detected_language", "priority": 6, "singleton": True})
    blocks.extend(
        [
            {"category": "sop", "content": block, "source": "sop", "priority": 10}
            for block in sop_blocks
            if str(block or "").strip()
        ],
    )
    blocks.append({"category": "grounding_policy", "content": grounding_rules, "source": "grounding", "priority": 20, "singleton": True})
    evidence_entries = [
        ("memory_constraints", "constraints", 30),
        ("memory_facts", "facts", 31),
        ("memory_procedures", "procedures", 32),
        ("memory_continuity", "continuity", 33),
    ]
    for category, key, priority in evidence_entries:
        content = str(evidence_blocks.get(key) or "").strip()
        if content:
            blocks.append({"category": category, "content": content, "source": "memory_evidence", "priority": priority})
    citation_text = str(citation_block or "").strip()
    if citation_text:
        blocks.append(
            {
                "category": "citation_refs",
                "content": citation_text,
                "source": "citations",
                "priority": 40,
            }
        )
    memory_text = str(memory_context or "").strip()
    if memory_text:
        blocks.append(
            {
                "category": "memory_context",
                "content": memory_text,
                "source": "memory",
                "priority": 25,
                "singleton": True,
            }
        )
    return blocks


def build_standard_prompt_plan(
    *,
    provider_style: str,
    conversation_rows: list[dict[str, Any]],
    l0_meta_rules: str,
    sop_blocks: list[str],
    grounding_rules: str,
    evidence_blocks: dict[str, str],
    citation_block: str,
    citations: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    memory_context: str | None = None,
    detected_language: str = "unknown",
) -> NormalizedPromptPlan:
    raw_blocks = build_default_system_blocks(
        l0_meta_rules=l0_meta_rules,
        sop_blocks=sop_blocks,
        grounding_rules=grounding_rules,
        evidence_blocks=evidence_blocks,
        citation_block=citation_block,
        memory_context=memory_context,
        detected_language=detected_language,
    )
    return build_prompt_plan(
        provider_style=provider_style,
        raw_system_blocks=raw_blocks,
        conversation_rows=conversation_rows,
        citations=citations,
        metadata=metadata,
    )


def build_prompt_plan(
    *,
    provider_style: str,
    raw_system_blocks: list[SystemBlock | dict[str, Any] | str],
    conversation_rows: list[dict[str, Any]],
    citations: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> NormalizedPromptPlan:
    deduped_system = dedupe_and_merge_system_blocks(build_system_blocks(raw_system_blocks))
    conversation_items = [
        ConversationItem(
            role=str(row.get("role") or "user"),
            content=row.get("content"),
            name=str(row.get("name")) if row.get("name") is not None else None,
        )
        for row in conversation_rows
    ]
    citation_items = [
        CitationItem(
            memory_ref=str(row.get("memory_ref") or "memory"),
            snippet=str(row.get("snippet") or ""),
        )
        for row in (citations or [])
    ]
    return NormalizedPromptPlan(
        provider_style=provider_style,
        system_blocks=deduped_system,
        conversation_items=conversation_items,
        citations=citation_items,
        metadata=dict(metadata or {}),
    )
