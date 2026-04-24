from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SystemBlock:
    category: str
    content: str
    source: str = ""
    priority: int = 100
    singleton: bool = False


def build_system_blocks(items: list[SystemBlock | dict[str, Any] | str], *, default_category: str = "injected_system") -> list[SystemBlock]:
    blocks: list[SystemBlock] = []
    for item in items:
        block = _coerce_block(item=item, default_category=default_category)
        if block is None:
            continue
        blocks.append(block)
    return blocks


def dedupe_and_merge_system_blocks(blocks: list[SystemBlock]) -> list[SystemBlock]:
    ranked = sorted(enumerate(blocks), key=lambda row: (row[1].priority, row[0]))
    deduped_by_text: list[SystemBlock] = []
    seen_text: set[str] = set()
    for _, block in ranked:
        normalized = _normalize_text(block.content)
        if not normalized or normalized in seen_text:
            continue
        seen_text.add(normalized)
        deduped_by_text.append(block)

    merged: list[SystemBlock] = []
    seen_singleton: set[str] = set()
    grouped: dict[str, list[SystemBlock]] = {}
    for block in deduped_by_text:
        if block.singleton:
            if block.category in seen_singleton:
                continue
            seen_singleton.add(block.category)
            merged.append(block)
            continue
        grouped.setdefault(block.category, []).append(block)

    for category, rows in grouped.items():
        lines = _dedupe_lines([row.content for row in rows])
        if not lines:
            continue
        first = rows[0]
        merged.append(
            SystemBlock(
                category=category,
                content="\n".join(lines),
                source=first.source,
                priority=first.priority,
                singleton=False,
            )
        )
    merged.sort(key=lambda row: row.priority)
    return _drop_redundant_citation_placeholders(merged)


def render_system_blocks_for_provider(blocks: list[SystemBlock], *, provider_style: str) -> list[str]:
    rendered: list[str] = []
    for block in blocks:
        text = block.content.strip()
        if not text:
            continue
        if provider_style == "anthropic":
            if not text.startswith("<"):
                tag = _category_to_xml_tag(block.category)
                text = f"<{tag}>\n{text}\n</{tag}>"
        elif provider_style == "openai":
            if not text.startswith(("#", "<")):
                heading = _category_to_heading(block.category)
                text = f"## {heading}\n{text}"
        rendered.append(text)
    return rendered


_CATEGORY_XML_TAG_MAP = {
    "meta_rules": "nexus_rules",
    "grounding_policy": "grounding",
    "memory_constraints": "constraints",
    "memory_facts": "verified_facts",
    "memory_procedures": "procedures",
    "memory_continuity": "session_context",
    "citation_refs": "citations",
    "memory_context": "nexus_context",
    "sop": "sop",
}

_CATEGORY_HEADING_MAP = {
    "meta_rules": "Core Rules",
    "grounding_policy": "Grounding Policy",
    "memory_constraints": "Constraints",
    "memory_facts": "Verified Facts",
    "memory_procedures": "Procedures",
    "memory_continuity": "Session Context",
    "citation_refs": "Citations",
    "memory_context": "Memory Context",
    "sop": "SOP",
}


def _category_to_xml_tag(category: str) -> str:
    return _CATEGORY_XML_TAG_MAP.get(category, category.replace(" ", "_"))


def _category_to_heading(category: str) -> str:
    return _CATEGORY_HEADING_MAP.get(category, category.replace("_", " ").title())


def _coerce_block(*, item: SystemBlock | dict[str, Any] | str, default_category: str) -> SystemBlock | None:
    if isinstance(item, SystemBlock):
        return item if item.content.strip() else None
    if isinstance(item, str):
        return SystemBlock(category=default_category, content=item.strip())
    if not isinstance(item, dict):
        return None
    content = str(item.get("content") or "").strip()
    if not content:
        return None
    return SystemBlock(
        category=str(item.get("category") or default_category).strip() or default_category,
        content=content,
        source=str(item.get("source") or "").strip(),
        priority=int(item.get("priority") or 100),
        singleton=bool(item.get("singleton")),
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _dedupe_lines(chunks: list[str]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        for line in chunk.splitlines():
            stripped = line.strip()
            normalized = _normalize_text(stripped)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            lines.append(stripped)
    return lines


def _drop_redundant_citation_placeholders(blocks: list[SystemBlock]) -> list[SystemBlock]:
    has_memory = any(block.category.startswith("memory_") for block in blocks)
    if not has_memory:
        return blocks
    filtered: list[SystemBlock] = []
    for block in blocks:
        normalized = _normalize_text(block.content)
        if block.category == "citation_refs" and normalized in {"citation refs: none", "citation refs:none"}:
            continue
        filtered.append(block)
    return filtered

