from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from nexusgate.router.capability_registry import CapabilityRegistry, ModelCapability
from nexusgate.router.provider_health import ProviderHealth


@dataclass(slots=True)
class RouteDecision:
    provider: str
    model: str
    api_base: str | None
    api_key: str | None
    render_mode: str
    routing_reason: str
    fallbacks: list[str]


class ProviderRouter:
    def __init__(self, registry: CapabilityRegistry | None = None, health: ProviderHealth | None = None) -> None:
        self.registry = registry or CapabilityRegistry()
        self.health = health or ProviderHealth()

    def route(
        self,
        *,
        normalized_req: Any,
        memory_pack_size: int,
        defaults: dict[str, Any],
    ) -> RouteDecision:
        requested_model = str(getattr(normalized_req, "requested_model", "") or "").strip()
        if requested_model and requested_model != "auto":
            resolved = self.registry.resolve(requested_model)
            provider = resolved.provider if resolved else "openai"
            render_mode = resolved.render_mode if resolved else "openai"
            fallbacks = self._fallback_models(primary_model=requested_model)
            api_base, api_key = self._resolve_connection(capability=resolved, defaults=defaults)
            return RouteDecision(
                provider=provider,
                model=requested_model,
                api_base=api_base,
                api_key=api_key,
                render_mode=render_mode,
                routing_reason="explicit_model",
                fallbacks=fallbacks,
            )

        task_type = str((getattr(normalized_req, "metadata", {}) or {}).get("task_type") or "chat")
        candidates = self._rank_candidates(
            task_type=task_type,
            tool_required=bool(getattr(normalized_req, "tool_required", False)),
            stream_required=bool(getattr(normalized_req, "stream", False)),
            memory_pack_size=memory_pack_size,
        )
        primary = candidates[0] if candidates else None
        if primary is None:
            model = str(defaults.get("model") or "")
            fallbacks = self._fallback_models(primary_model=model)
            return RouteDecision(
                provider="openai",
                model=model,
                api_base=defaults.get("api_base"),
                api_key=defaults.get("api_key"),
                render_mode="openai",
                routing_reason="default_model_fallback",
                fallbacks=fallbacks,
            )

        fallbacks = [row.model for row in candidates[1:4]]
        api_base, api_key = self._resolve_connection(capability=primary, defaults=defaults)
        return RouteDecision(
            provider=primary.provider,
            model=primary.model,
            api_base=api_base,
            api_key=api_key,
            render_mode=primary.render_mode,
            routing_reason=f"auto_task={task_type}",
            fallbacks=fallbacks,
        )

    def _rank_candidates(
        self,
        *,
        task_type: str,
        tool_required: bool,
        stream_required: bool,
        memory_pack_size: int,
    ) -> list[ModelCapability]:
        scored: list[tuple[float, ModelCapability]] = []
        for row in self.registry.all():
            if self.health.is_circuit_open(row.provider):
                continue
            if tool_required and not row.supports_tools:
                continue
            if stream_required and not row.supports_stream:
                continue
            score = row.quality_tier * 2.0
            score -= row.cost_tier * 0.4
            score += self.health.score(row.provider) * 1.5
            if memory_pack_size > 1800:
                score += min(row.context_window / 100000.0, 3.0)
            if task_type in {"coding", "debug"} and row.supports_tools:
                score += 1.0
            if task_type == "planning":
                score += row.quality_tier * 0.4
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored]

    def _fallback_models(self, primary_model: str) -> list[str]:
        ordered = [row.model for row in self.registry.all() if row.model != primary_model]
        return ordered[:3]

    @staticmethod
    def _resolve_connection(capability: ModelCapability | None, defaults: dict[str, Any]) -> tuple[str | None, str | None]:
        if capability is None:
            return defaults.get("api_base"), defaults.get("api_key")
        api_base = capability.api_base or defaults.get("api_base")
        api_key = defaults.get("api_key")
        if capability.api_key_env:
            env_value = os.getenv(capability.api_key_env)
            if env_value:
                api_key = env_value
        return api_base, api_key
