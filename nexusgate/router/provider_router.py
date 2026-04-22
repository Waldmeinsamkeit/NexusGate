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
    reason_codes: list[str]
    fallback_chain: list[str]
    context_budget: int
    grounding_mode: str
    tool_mode: str


class ProviderRouter:
    def __init__(self, registry: CapabilityRegistry | None = None, health: ProviderHealth | None = None) -> None:
        self.registry = registry or CapabilityRegistry()
        self.health = health or ProviderHealth()

    def route(
        self,
        *,
        normalized_req: Any,
        memory_pack_size: int,
        pack_features: dict[str, Any] | None = None,
        risk_profile: dict[str, Any] | None = None,
        defaults: dict[str, Any],
    ) -> RouteDecision:
        pack_features = pack_features or {}
        risk_profile = risk_profile or {}
        requested_model = str(getattr(normalized_req, "requested_model", "") or "").strip()
        if requested_model and requested_model != "auto":
            resolved = self.registry.resolve(requested_model)
            provider = resolved.provider if resolved else "openai"
            render_mode = resolved.render_mode if resolved else "openai"
            fallbacks = self._fallback_models(primary_model=requested_model, primary_provider=provider)
            api_base, api_key = self._resolve_connection(capability=resolved, defaults=defaults)
            context_budget = self._context_budget_for(capability=resolved, memory_pack_size=memory_pack_size, pack_features=pack_features)
            return RouteDecision(
                provider=provider,
                model=requested_model,
                api_base=api_base,
                api_key=api_key,
                render_mode=render_mode,
                routing_reason="explicit_model",
                fallbacks=fallbacks,
                reason_codes=["explicit_model"],
                fallback_chain=fallbacks,
                context_budget=context_budget,
                grounding_mode=self._grounding_mode(risk_profile=risk_profile, pack_features=pack_features),
                tool_mode="required" if bool(getattr(normalized_req, "tool_required", False)) else "optional",
            )

        task_type = str((getattr(normalized_req, "metadata", {}) or {}).get("task_type") or "chat")
        reason_codes = [f"auto_task={task_type}"]
        if bool(pack_features.get("contains_l4")):
            reason_codes.append("contains_l4")
        if int(pack_features.get("estimated_tokens") or memory_pack_size) > 1800:
            reason_codes.append("long_context")
        risk_level = str(risk_profile.get("risk_level") or "low")
        if risk_level in {"medium", "high", "critical"}:
            reason_codes.append(f"risk={risk_level}")
        candidates = self._rank_candidates(
            task_type=task_type,
            tool_required=bool(getattr(normalized_req, "tool_required", False)),
            stream_required=bool(getattr(normalized_req, "stream", False)),
            memory_pack_size=memory_pack_size,
            pack_features=pack_features,
            risk_profile=risk_profile,
        )
        primary = candidates[0] if candidates else None
        if primary is None:
            model = str(defaults.get("model") or "")
            fallbacks = self._fallback_models(primary_model=model, primary_provider="openai")
            return RouteDecision(
                provider="openai",
                model=model,
                api_base=defaults.get("api_base"),
                api_key=defaults.get("api_key"),
                render_mode="openai",
                routing_reason="default_model_fallback",
                fallbacks=fallbacks,
                reason_codes=["default_model_fallback"],
                fallback_chain=fallbacks,
                context_budget=max(int(memory_pack_size * 1.3), memory_pack_size),
                grounding_mode=self._grounding_mode(risk_profile=risk_profile, pack_features=pack_features),
                tool_mode="required" if bool(getattr(normalized_req, "tool_required", False)) else "optional",
            )

        fallbacks = [row.model for row in candidates[1:4] if row.provider == primary.provider]
        api_base, api_key = self._resolve_connection(capability=primary, defaults=defaults)
        context_budget = self._context_budget_for(capability=primary, memory_pack_size=memory_pack_size, pack_features=pack_features)
        return RouteDecision(
            provider=primary.provider,
            model=primary.model,
            api_base=api_base,
            api_key=api_key,
            render_mode=primary.render_mode,
            routing_reason=f"auto_task={task_type}",
            fallbacks=fallbacks,
            reason_codes=reason_codes,
            fallback_chain=fallbacks,
            context_budget=context_budget,
            grounding_mode=self._grounding_mode(risk_profile=risk_profile, pack_features=pack_features),
            tool_mode="required" if bool(getattr(normalized_req, "tool_required", False)) else "optional",
        )

    def _rank_candidates(
        self,
        *,
        task_type: str,
        tool_required: bool,
        stream_required: bool,
        memory_pack_size: int,
        pack_features: dict[str, Any],
        risk_profile: dict[str, Any],
    ) -> list[ModelCapability]:
        scored: list[tuple[float, ModelCapability]] = []
        estimated_tokens = int(pack_features.get("estimated_tokens") or memory_pack_size)
        verified_ratio = float(pack_features.get("verified_ratio") or 0.0)
        continuity_weight = float(pack_features.get("continuity_weight") or 0.0)
        citation_density = float(pack_features.get("citation_density") or 0.0)
        risk_level = str(risk_profile.get("risk_level") or "low")
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
            if estimated_tokens > 1800:
                score += min(row.context_window / 100000.0, 3.0)
            if task_type in {"coding", "debug"} and row.supports_tools:
                score += 1.0
            if task_type == "planning":
                score += row.quality_tier * 0.4
            if risk_level in {"high", "critical"}:
                if row.provider == "anthropic":
                    score += 2.2
                if citation_density < 0.3 and row.quality_tier >= 5:
                    score += 0.8
            if verified_ratio < 0.5 and row.quality_tier >= 5:
                score += 0.8
            if continuity_weight >= 0.35 and row.cost_tier <= 2:
                score += 0.5
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored]

    def _fallback_models(self, primary_model: str, primary_provider: str) -> list[str]:
        ordered = [
            row.model
            for row in self.registry.all()
            if row.model != primary_model and row.provider == primary_provider
        ]
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

    @staticmethod
    def _grounding_mode(*, risk_profile: dict[str, Any], pack_features: dict[str, Any]) -> str:
        risk_level = str(risk_profile.get("risk_level") or "low")
        has_verified_ratio = "verified_ratio" in pack_features
        verified_ratio = float(pack_features.get("verified_ratio") or 0.0)
        if risk_level in {"high", "critical"} or (has_verified_ratio and verified_ratio < 0.4):
            return "strict"
        if risk_level == "medium":
            return "balanced"
        if has_verified_ratio and verified_ratio < 0.75:
            return "balanced"
        return "relaxed"

    @staticmethod
    def _context_budget_for(
        *,
        capability: ModelCapability | None,
        memory_pack_size: int,
        pack_features: dict[str, Any],
    ) -> int:
        estimated_tokens = int(pack_features.get("estimated_tokens") or memory_pack_size)
        if capability is None:
            return max(estimated_tokens, int(estimated_tokens * 1.2))
        target = max(estimated_tokens, int(estimated_tokens * 1.25))
        hard_cap = int(capability.context_window * 0.85)
        return min(target, hard_cap)
