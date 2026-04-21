from __future__ import annotations

from typing import Any


def build_citations(memory_context: str, session_id: str, max_items: int = 4) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not memory_context.strip():
        return rows
    for idx, line in enumerate(memory_context.splitlines(), start=1):
        text = line.strip()
        if not text or text == "(empty)":
            continue
        if not text.startswith("[L"):
            continue
        rows.append(
            {
                "memory_ref": f"{session_id}:{idx}",
                "snippet": text[:180],
                "source_type": "memory",
            }
        )
        if len(rows) >= max_items:
            break
    return rows

