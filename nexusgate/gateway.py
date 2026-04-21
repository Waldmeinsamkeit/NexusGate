from __future__ import annotations

from typing import Any

from litellm import completion

from nexusgate.router import ProviderRouter


class LiteLLMGateway:
    def __init__(
        self,
        timeout_seconds: int = 120,
        llmapi_base_url: str | None = None,
        llmapi_api_key: str | None = None,
        llmapi_model_prefix: str = "llmapi/",
        llmapi_provider_prefix: str = "openai/",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.llmapi_base_url = llmapi_base_url
        self.llmapi_api_key = llmapi_api_key
        self.llmapi_model_prefix = llmapi_model_prefix
        self.llmapi_provider_prefix = llmapi_provider_prefix

    def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        kwargs = dict(payload)
        kwargs = self._inject_third_party_route(kwargs)
        kwargs["timeout"] = self.timeout_seconds
        response = completion(**kwargs)

        if hasattr(response, "model_dump"):
            return response.model_dump()
        if isinstance(response, dict):
            return response
        return dict(response)

    def _inject_third_party_route(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        model = str(kwargs.get("model", "")).strip()
        if not model.startswith(self.llmapi_model_prefix):
            return kwargs
        if not self.llmapi_base_url or not self.llmapi_api_key:
            return kwargs

        raw_model = model[len(self.llmapi_model_prefix) :]
        if not raw_model:
            return kwargs

        kwargs["model"] = f"{self.llmapi_provider_prefix}{raw_model}"
        kwargs["api_base"] = self.llmapi_base_url
        kwargs["api_key"] = self.llmapi_api_key
        return kwargs


def route(
    normalized_req: Any,
    defaults: dict[str, Any],
    *,
    memory_pack_size: int = 0,
    router: ProviderRouter | None = None,
) -> dict[str, Any]:
    provider_router = router or ProviderRouter()
    decision = provider_router.route(
        normalized_req=normalized_req,
        memory_pack_size=memory_pack_size,
        defaults=defaults,
    )
    return {
        "provider": decision.provider,
        "model": decision.model,
        "api_base": decision.api_base,
        "api_key": decision.api_key,
        "render_mode": decision.render_mode,
        "routing_reason": decision.routing_reason,
        "fallbacks": decision.fallbacks,
    }
