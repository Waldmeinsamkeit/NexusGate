from __future__ import annotations

from typing import Any, Callable

from nexusgate.config import settings
from nexusgate.prompting.plan import NormalizedPromptPlan
from nexusgate.prompting.renderers import (
    render_plan_to_messages,
    render_plan_to_responses_payload,
)
from nexusgate.prompting.responses_budget import budget_native_responses_payload


def prepare_prompt_for_provider(
    *,
    prompt_plan: NormalizedPromptPlan,
    context_budget_tokens: int | None,
    mode: str,
    responses_payload: dict[str, Any] | None = None,
    apply_total_context_budget: Callable[[list[dict[str, Any]], int | None], tuple[list[dict[str, Any]], dict[str, int | float | bool | str]]],
    responses_payload_to_messages: Callable[[dict[str, Any]], list[dict[str, Any]]],
    messages_to_responses_payload: Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]],
) -> tuple[Any, dict[str, int | float | bool | str]]:
    if mode == "messages":
        enhanced_messages = render_plan_to_messages(prompt_plan)
        return apply_total_context_budget(enhanced_messages, context_budget_tokens)

    if mode != "responses" or responses_payload is None:
        return [], {
            "enabled": False,
            "before_tokens": 0,
            "after_tokens": 0,
            "context_budget_tokens": int(context_budget_tokens or 0),
            "prompt_budget_tokens": 0,
            "truncated_messages": 0,
            "dropped_messages": 0,
            "over_budget_before": False,
            "over_budget_after": False,
            "skipped": True,
            "skip_reason": "invalid_prepare_mode",
        }

    prepared_payload = render_plan_to_responses_payload(responses_payload, prompt_plan)
    if prepared_payload.get("tools"):
        return budget_native_responses_payload(
            prepared_payload,
            context_budget_tokens=int(context_budget_tokens or 0),
            reserve_ratio=float(settings.context_budget_response_reserve_ratio or 0.3),
        )

    passthrough_budget_messages = responses_payload_to_messages(prepared_payload)
    passthrough_budget_messages, budget_report = apply_total_context_budget(
        passthrough_budget_messages,
        context_budget_tokens,
    )
    return messages_to_responses_payload(prepared_payload, passthrough_budget_messages), budget_report

