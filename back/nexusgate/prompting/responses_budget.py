from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolEpisode:
    start_index: int
    end_index: int
    item_indices: list[int]
    assistant_summaries: list[str]
    tool_calls: list[str]
    tool_results: list[str]


def budget_native_responses_payload(
    payload: dict[str, Any],
    *,
    context_budget_tokens: int | None,
    reserve_ratio: float = 0.3,
) -> tuple[dict[str, Any], dict[str, int | float | bool | str]]:
    patched = copy.deepcopy(payload)
    input_items = patched.get("input")
    if not isinstance(input_items, list):
        return patched, _skip_report(context_budget_tokens, "input_not_list")
    if not any(isinstance(item, dict) and "role" in item for item in input_items):
        return patched, _skip_report(context_budget_tokens, "input_not_role_items")

    before_tokens = _estimate_items_tokens(input_items)
    prompt_budget = _prompt_budget_tokens(context_budget_tokens, reserve_ratio=reserve_ratio)
    if prompt_budget <= 0 or before_tokens <= prompt_budget:
        return patched, _pass_report(before_tokens, context_budget_tokens, prompt_budget)

    episodes = extract_tool_episodes_from_responses_input(input_items)
    if not episodes:
        return patched, _skip_report(context_budget_tokens, "no_tool_episodes", before_tokens=before_tokens, prompt_budget=prompt_budget)

    trimmed = trim_tool_episodes_to_budget(input_items, episodes, prompt_budget_tokens=prompt_budget)
    patched["input"] = render_tool_episodes_to_responses_input(input_items, trimmed["episode_items"])
    after_tokens = _estimate_items_tokens(patched["input"])
    report: dict[str, int | float | bool | str] = {
        "enabled": True,
        "native_tools_budget": True,
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
        "context_budget_tokens": int(context_budget_tokens or 0),
        "prompt_budget_tokens": prompt_budget,
        "truncated_messages": int(trimmed["truncated"]),
        "dropped_messages": int(trimmed["dropped"]),
        "episode_count": len(episodes),
        "episodes_trimmed": int(trimmed["episodes_trimmed"]),
        "episodes_summarized": int(trimmed["episodes_summarized"]),
        "tool_result_pruned_chars": int(trimmed["result_pruned_chars"]),
        "over_budget_before": before_tokens > prompt_budget,
        "over_budget_after": after_tokens > prompt_budget,
    }
    return patched, report


def extract_tool_episodes_from_responses_input(input_items: list[Any]) -> list[ToolEpisode]:
    episodes: list[ToolEpisode] = []
    idx = 0
    total = len(input_items)
    while idx < total:
        item = input_items[idx]
        if not (_is_role_item(item) and _is_tool_call_item(item)):
            idx += 1
            continue
        start = idx
        if idx > 0 and _is_role_item(input_items[idx - 1]) and _role(input_items[idx - 1]) == "assistant" and not _is_tool_call_item(input_items[idx - 1]):
            start = idx - 1
        end = idx
        while end + 1 < total:
            nxt = input_items[end + 1]
            if not _is_role_item(nxt):
                break
            role = _role(nxt)
            if role in {"user", "system"}:
                break
            # New assistant tool-call indicates a new episode boundary.
            if role == "assistant" and _is_tool_call_item(nxt):
                break
            if role in {"tool", "assistant"}:
                end += 1
                continue
            break
        episode_items = [input_items[i] for i in range(start, end + 1)]
        episodes.append(_build_episode(start, end, episode_items))
        idx = end + 1
    return episodes


def trim_tool_episodes_to_budget(
    input_items: list[Any],
    episodes: list[ToolEpisode],
    *,
    prompt_budget_tokens: int,
    keep_recent_episodes: int = 2,
) -> dict[str, Any]:
    total_tokens = _estimate_items_tokens(input_items)
    episode_map = {ep.start_index: ep for ep in episodes}
    rendered: list[dict[str, Any]] = []
    dropped = 0
    truncated = 0
    episodes_trimmed = 0
    episodes_summarized = 0
    result_pruned_chars = 0
    protected_starts = {ep.start_index for ep in episodes[-max(1, keep_recent_episodes):]}

    idx = 0
    while idx < len(input_items):
        ep = episode_map.get(idx)
        if ep is None:
            row = _coerce_item(input_items[idx])
            rendered.append(row)
            idx += 1
            continue
        if ep.start_index in protected_starts:
            rows, changed, pruned_chars = _minify_episode_rows(input_items[ep.start_index : ep.end_index + 1])
            rendered.extend(rows)
            truncated += changed
            result_pruned_chars += pruned_chars
            if changed > 0:
                episodes_trimmed += 1
        else:
            rendered.append(_episode_summary_item(ep))
            dropped += max(len(ep.item_indices) - 1, 0)
            episodes_summarized += 1
        idx = ep.end_index + 1

    if _estimate_items_tokens(rendered) > prompt_budget_tokens:
        rendered, extra = _shrink_long_text_blocks(rendered, max_chars=320)
        truncated += extra
    if _estimate_items_tokens(rendered) > prompt_budget_tokens:
        rendered = _drop_oldest_tool_items(rendered)
        dropped += 1
    return {
        "episode_items": rendered,
        "truncated": truncated,
        "dropped": dropped,
        "before_tokens": total_tokens,
        "episodes_trimmed": episodes_trimmed,
        "episodes_summarized": episodes_summarized,
        "result_pruned_chars": result_pruned_chars,
    }


def render_tool_episodes_to_responses_input(_original_items: list[Any], episode_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return episode_items


def minify_tool_arguments(arguments: Any, *, max_chars: int = 240) -> str:
    text = _stringify(arguments)
    if len(text) <= max_chars:
        return text
    obj = _try_parse_json(text)
    if obj is None:
        return head_tail_shrink(text, max_chars=max_chars)
    reduced = _prune_json_value(obj, depth=2, max_items=6)
    return head_tail_shrink(json.dumps(reduced, ensure_ascii=False), max_chars=max_chars)


def prune_tool_result_json(value: Any, *, max_chars: int = 420) -> str:
    text = _stringify(value)
    if len(text) <= max_chars:
        return text
    obj = _try_parse_json(text)
    if obj is None:
        return head_tail_shrink(text, max_chars=max_chars)
    reduced = _prune_json_value(obj, depth=2, max_items=8)
    return head_tail_shrink(json.dumps(reduced, ensure_ascii=False), max_chars=max_chars)


def head_tail_shrink(text: str, *, max_chars: int = 320) -> str:
    if len(text) <= max_chars:
        return text
    head = max(80, int(max_chars * 0.55))
    tail = max_chars - head - 14
    if tail < 30:
        tail = 30
    return f"{text[:head]} ...[trimmed]... {text[-tail:]}"


def summarize_tool_result(text: str, *, max_chars: int = 220) -> str:
    compact = " ".join((text or "").split())
    if not compact:
        return "no result"
    if len(compact) <= max_chars:
        return compact
    return head_tail_shrink(compact, max_chars=max_chars)


def _build_episode(start: int, end: int, items: list[Any]) -> ToolEpisode:
    summaries: list[str] = []
    calls: list[str] = []
    results: list[str] = []
    for row in items:
        if not _is_role_item(row):
            continue
        role = _role(row)
        if role == "assistant":
            if _is_tool_call_item(row):
                calls.append(_extract_call_signature(row))
            else:
                summaries.append(_item_text(row))
        elif role == "tool":
            results.append(_item_text(row))
    return ToolEpisode(start, end, list(range(start, end + 1)), summaries, calls, results)


def _minify_episode_rows(rows: list[Any]) -> tuple[list[dict[str, Any]], int, int]:
    out: list[dict[str, Any]] = []
    changed = 0
    pruned_chars = 0
    for row in rows:
        item = _coerce_item(row)
        role = _role(item)
        if role == "assistant" and _is_tool_call_item(item):
            patched, diff, removed_chars = _minify_call_item(item)
            out.append(patched)
            changed += diff
            pruned_chars += removed_chars
            continue
        if role == "tool":
            patched, diff, removed_chars = _minify_tool_result_item(item)
            out.append(patched)
            changed += diff
            pruned_chars += removed_chars
            continue
        out.append(item)
    return out, changed, pruned_chars


def _episode_summary_item(ep: ToolEpisode) -> dict[str, Any]:
    call = ep.tool_calls[0] if ep.tool_calls else "tool_call"
    result = summarize_tool_result(ep.tool_results[0] if ep.tool_results else "no result", max_chars=180)
    summary = f"Tool episode summary: call={call}; result={result}"
    return {"role": "assistant", "content": [{"type": "input_text", "text": summary}]}


def _minify_call_item(item: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    patched = copy.deepcopy(item)
    changed = 0
    removed_chars = 0
    content = patched.get("content")
    if not isinstance(content, list):
        return patched, changed, removed_chars
    new_content: list[Any] = []
    for block in content:
        if isinstance(block, dict) and _is_tool_call_block(block):
            updated = dict(block)
            if "arguments" in updated:
                original = _stringify(updated.get("arguments"))
                updated["arguments"] = minify_tool_arguments(updated.get("arguments"), max_chars=240)
                if _stringify(updated.get("arguments")) != original:
                    changed += 1
                    removed_chars += max(len(original) - len(_stringify(updated.get("arguments"))), 0)
            new_content.append(updated)
            continue
        new_content.append(block)
    patched["content"] = new_content
    return patched, changed, removed_chars


def _minify_tool_result_item(item: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    patched = copy.deepcopy(item)
    changed = 0
    removed_chars = 0
    content = patched.get("content")
    if isinstance(content, str):
        shrunk = summarize_tool_result(prune_tool_result_json(content, max_chars=420), max_chars=220)
        if shrunk != content:
            patched["content"] = [{"type": "input_text", "text": shrunk}]
            changed += 1
            removed_chars += max(len(content) - len(shrunk), 0)
        return patched, changed, removed_chars
    if not isinstance(content, list):
        return patched, changed, removed_chars
    new_content: list[Any] = []
    for block in content:
        if isinstance(block, dict) and "text" in block:
            original = _stringify(block.get("text"))
            shrunk = summarize_tool_result(prune_tool_result_json(block.get("text"), max_chars=420), max_chars=220)
            if shrunk != original:
                updated = dict(block)
                updated["text"] = shrunk
                new_content.append(updated)
                changed += 1
                removed_chars += max(len(original) - len(shrunk), 0)
                continue
        new_content.append(block)
    patched["content"] = new_content
    return patched, changed, removed_chars


def _drop_oldest_tool_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = list(items)
    for idx, item in enumerate(out):
        if _role(item) in {"tool"}:
            out.pop(idx)
            return out
    return out


def _shrink_long_text_blocks(items: list[dict[str, Any]], *, max_chars: int) -> tuple[list[dict[str, Any]], int]:
    changed = 0
    out: list[dict[str, Any]] = []
    for item in items:
        patched = copy.deepcopy(item)
        content = patched.get("content")
        if isinstance(content, str):
            shrunk = head_tail_shrink(content, max_chars=max_chars)
            if shrunk != content:
                patched["content"] = shrunk
                changed += 1
            out.append(patched)
            continue
        if not isinstance(content, list):
            out.append(patched)
            continue
        new_content: list[Any] = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text = _stringify(block.get("text"))
                shrunk = head_tail_shrink(text, max_chars=max_chars)
                if shrunk != text:
                    updated = dict(block)
                    updated["text"] = shrunk
                    new_content.append(updated)
                    changed += 1
                    continue
            new_content.append(block)
        patched["content"] = new_content
        out.append(patched)
    return out, changed


def _prompt_budget_tokens(context_budget_tokens: int | None, *, reserve_ratio: float) -> int:
    total = int(context_budget_tokens or 0)
    if total <= 0:
        return 0
    reserve = int(total * max(0.0, min(reserve_ratio, 0.8)))
    return max(total - reserve, 1)


def _estimate_items_tokens(items: list[Any]) -> int:
    total_chars = sum(len(_stringify(item)) for item in items)
    return max(total_chars // 4, 1)


def _is_role_item(item: Any) -> bool:
    return isinstance(item, dict) and isinstance(item.get("role"), str)


def _role(item: dict[str, Any]) -> str:
    return str(item.get("role") or "").strip().lower()


def _is_tool_call_item(item: dict[str, Any]) -> bool:
    if item.get("tool_calls"):
        return True
    content = item.get("content")
    if not isinstance(content, list):
        return False
    return any(isinstance(block, dict) and _is_tool_call_block(block) for block in content)


def _is_tool_call_block(block: dict[str, Any]) -> bool:
    block_type = str(block.get("type") or "").lower()
    if block_type in {"tool_call", "function_call", "output_tool_call", "tool_use"}:
        return True
    return bool(block.get("name")) and ("arguments" in block)


def _extract_call_signature(item: dict[str, Any]) -> str:
    if item.get("tool_calls"):
        calls = item.get("tool_calls") or []
        names = [str((call or {}).get("function", {}).get("name") or (call or {}).get("name") or "tool") for call in calls[:2]]
        return ", ".join(names)
    content = item.get("content")
    if not isinstance(content, list):
        return "tool_call"
    names: list[str] = []
    for block in content:
        if isinstance(block, dict) and _is_tool_call_block(block):
            names.append(str(block.get("name") or block.get("tool_name") or "tool"))
    return ", ".join(names[:2]) if names else "tool_call"


def _item_text(item: dict[str, Any]) -> str:
    content = item.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return _stringify(content)
    chunks: list[str] = []
    for block in content:
        if isinstance(block, dict) and "text" in block:
            chunks.append(_stringify(block.get("text")))
        elif isinstance(block, str):
            chunks.append(block)
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _coerce_item(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    return {"role": "user", "content": [{"type": "input_text", "text": _stringify(item)}]}


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _try_parse_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def _prune_json_value(value: Any, *, depth: int, max_items: int) -> Any:
    if depth <= 0:
        return "..."
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= max_items:
                out["..."] = f"{len(value) - max_items} more keys"
                break
            out[str(key)] = _prune_json_value(item, depth=depth - 1, max_items=max_items)
        return out
    if isinstance(value, list):
        out = [_prune_json_value(item, depth=depth - 1, max_items=max_items) for item in value[:max_items]]
        if len(value) > max_items:
            out.append(f"... {len(value) - max_items} more items")
        return out
    return value


def _skip_report(
    context_budget_tokens: int | None,
    reason: str,
    *,
    before_tokens: int = 0,
    prompt_budget: int = 0,
) -> dict[str, int | float | bool | str]:
    return {
        "enabled": False,
        "native_tools_budget": False,
        "before_tokens": before_tokens,
        "after_tokens": before_tokens,
        "context_budget_tokens": int(context_budget_tokens or 0),
        "prompt_budget_tokens": prompt_budget,
        "truncated_messages": 0,
        "dropped_messages": 0,
        "over_budget_before": False,
        "over_budget_after": False,
        "skipped": True,
        "skip_reason": reason,
    }


def _pass_report(before_tokens: int, context_budget_tokens: int | None, prompt_budget: int) -> dict[str, int | float | bool | str]:
    return {
        "enabled": True,
        "native_tools_budget": True,
        "before_tokens": before_tokens,
        "after_tokens": before_tokens,
        "context_budget_tokens": int(context_budget_tokens or 0),
        "prompt_budget_tokens": prompt_budget,
        "truncated_messages": 0,
        "dropped_messages": 0,
        "over_budget_before": False,
        "over_budget_after": False,
    }
