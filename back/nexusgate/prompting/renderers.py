from __future__ import annotations

import copy
import json
from typing import Any

from nexusgate.prompting.plan import NormalizedPromptPlan
from nexusgate.prompting.system_blocks import render_system_blocks_for_provider


def render_plan_to_messages(plan: NormalizedPromptPlan) -> list[dict[str, Any]]:
    rendered_system = render_system_blocks_for_provider(
        plan.system_blocks,
        provider_style=plan.provider_style,
    )
    system_rows = [{"role": "system", "content": block} for block in rendered_system if block.strip()]
    conversation_rows = [
        _conversation_item_to_row(item)
        for item in plan.conversation_items
    ]
    return [*system_rows, *conversation_rows]


def render_plan_to_responses_payload(payload: dict[str, Any], plan: NormalizedPromptPlan) -> dict[str, Any]:
    patched = copy.deepcopy(payload)
    system_blocks = render_system_blocks_for_provider(plan.system_blocks, provider_style=plan.provider_style)
    system_text = "\n\n".join(block.strip() for block in system_blocks if block.strip()).strip()
    if not system_text:
        return patched

    instructions = patched.get("instructions")
    if isinstance(instructions, str) and instructions.strip():
        patched["instructions"] = f"{system_text}\n\n{instructions}"
        return patched

    system_item = {"role": "system", "content": [{"type": "input_text", "text": system_text}]}
    input_value = patched.get("input")
    if isinstance(input_value, list):
        patched["input"] = [system_item, *input_value]
        return patched
    if isinstance(input_value, str):
        patched["input"] = [
            system_item,
            {"role": "user", "content": [{"type": "input_text", "text": input_value}]},
        ]
        return patched
    if isinstance(input_value, dict):
        patched["input"] = [system_item, input_value]
        return patched
    patched["input"] = [system_item]
    return patched


def _conversation_item_to_row(item: Any) -> dict[str, Any]:
    row = {
        "role": str(getattr(item, "role", "user") or "user"),
        "content": getattr(item, "content", ""),
    }
    name = getattr(item, "name", None)
    if name is not None:
        row["name"] = str(name)
    if isinstance(row["content"], (dict, list, str)):
        return row
    row["content"] = json.dumps(row["content"], ensure_ascii=False)
    return row

