from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass(slots=True)
class ModelCapability:
    provider: str
    model: str
    context_window: int
    supports_tools: bool
    supports_stream: bool
    quality_tier: int
    cost_tier: int
    render_mode: str
    api_base: str | None = None
    api_key_env: str | None = None
    tags: list[str] = field(default_factory=list)


class CapabilityRegistry:
    def __init__(self, capabilities: list[ModelCapability] | None = None, config_path: str | None = None) -> None:
        if capabilities is not None:
            self._capabilities = capabilities
            return
        self._capabilities = self._load_capabilities(config_path=config_path)

    def resolve(self, requested_model: str) -> ModelCapability | None:
        requested = requested_model.strip().lower()
        for row in self._capabilities:
            if row.model.lower() == requested:
                return row
        return None

    def all(self) -> list[ModelCapability]:
        return list(self._capabilities)

    def _load_capabilities(self, config_path: str | None = None) -> list[ModelCapability]:
        path = config_path or os.getenv("NEXUSGATE_CAPABILITY_CONFIG")
        if path:
            loaded = self._load_from_file(path)
            if loaded:
                return loaded
        return self._default_capabilities()

    @staticmethod
    def _load_from_file(path: str) -> list[ModelCapability]:
        try:
            payload = json.loads(open(path, "r", encoding="utf-8").read())
        except Exception:
            return []
        rows = payload.get("models") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []
        capabilities: list[ModelCapability] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                capabilities.append(
                    ModelCapability(
                        provider=str(row.get("provider") or "openai"),
                        model=str(row["model"]),
                        context_window=int(row.get("context_window") or 32768),
                        supports_tools=bool(row.get("supports_tools", False)),
                        supports_stream=bool(row.get("supports_stream", True)),
                        quality_tier=int(row.get("quality_tier") or 3),
                        cost_tier=int(row.get("cost_tier") or 3),
                        render_mode=str(row.get("render_mode") or "openai"),
                        api_base=(str(row.get("api_base")) if row.get("api_base") else None),
                        api_key_env=(str(row.get("api_key_env")) if row.get("api_key_env") else None),
                        tags=[str(item) for item in (row.get("tags") or []) if str(item).strip()],
                    )
                )
            except Exception:
                continue
        return capabilities

    @staticmethod
    def _default_capabilities() -> list[ModelCapability]:
        return [
            ModelCapability(
                provider="openai",
                model="gpt-5.2-codex",
                context_window=128000,
                supports_tools=True,
                supports_stream=True,
                quality_tier=5,
                cost_tier=4,
                render_mode="openai",
                tags=["coding", "tool_use"],
            ),
            ModelCapability(
                provider="openai",
                model="gpt-4.1-mini",
                context_window=128000,
                supports_tools=True,
                supports_stream=True,
                quality_tier=3,
                cost_tier=2,
                render_mode="openai",
                tags=["fallback", "cheap"],
            ),
            ModelCapability(
                provider="anthropic",
                model="claude-sonnet-4-5-20250929",
                context_window=200000,
                supports_tools=True,
                supports_stream=True,
                quality_tier=5,
                cost_tier=4,
                render_mode="anthropic_messages",
                tags=["reasoning"],
            ),
            # Extension points for llmapi/openrouter style aggregation.
            ModelCapability(
                provider="llmapi",
                model="openrouter/deepseek-chat",
                context_window=64000,
                supports_tools=False,
                supports_stream=True,
                quality_tier=3,
                cost_tier=1,
                render_mode="openai",
                api_base=os.getenv("LLMAPI_BASE_URL"),
                api_key_env="LLMAPI_API_KEY",
                tags=["aggregator", "cheap"],
            ),
            ModelCapability(
                provider="llmapi",
                model="openrouter/qwen-plus",
                context_window=131072,
                supports_tools=True,
                supports_stream=True,
                quality_tier=4,
                cost_tier=2,
                render_mode="openai",
                api_base=os.getenv("LLMAPI_BASE_URL"),
                api_key_env="LLMAPI_API_KEY",
                tags=["aggregator", "balanced"],
            ),
        ]

