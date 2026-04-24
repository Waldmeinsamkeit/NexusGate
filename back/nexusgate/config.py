from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NexusGate-Core"
    app_env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    request_timeout_seconds: int = 120
    api_key_required: bool = False
    local_api_key: str | None = None
    local_api_key_store_path: str = "~/.nexusgate/secrets.json"
    client_sync_enabled: bool = True
    codex_config_path: str = "C:/Users/Administrator/.codex/config.toml"
    claude_settings_path: str = "C:/Users/Administrator/.claude/settings.json"
    codex_local_base_url: str = "http://127.0.0.1:8000/v1"
    claude_local_base_url: str = "http://127.0.0.1:8000"
    upstream_api_key_required: bool = True
    default_model: str = "claude-sonnet-4-5-20250929"
    target_provider: str = "claude-sonnet-4-5-20250929"
    target_base_url: str | None = None
    target_api_key: str | None = None
    llmapi_base_url: str | None = None
    llmapi_api_key: str | None = None
    llmapi_model_prefix: str = "llmapi/"
    llmapi_provider_prefix: str = "openai/"
    memory_enabled: bool = True
    memory_store_path: str = Field(default="memory")
    memory_source_root: str = Field(default=".")
    memory_collection_name: str = Field(default="nexusgate_memory")
    memory_top_k: int = 6
    memory_use_chroma: bool = False
    enable_memory_management_sop: bool = True
    enable_session_memory_recall_sop: bool = True
    session_memory_recall_mode: str = "auto"
    history_rewrite_enabled: bool = True
    history_rewrite_default_mode: str = "auto"
    history_rewrite_global_light_query_threshold: int = 120
    history_rewrite_light_keep_system: int = 0
    history_rewrite_light_keep_user: int = 1
    history_rewrite_light_keep_assistant: int = 0
    history_rewrite_light_keep_tool: int = 0
    history_rewrite_light_keep_other: int = 0
    history_rewrite_light_max_chars_per_message: int = 700
    history_rewrite_normal_keep_system: int = 1
    history_rewrite_normal_keep_user: int = 1
    history_rewrite_normal_keep_assistant: int = 1
    history_rewrite_normal_keep_tool: int = 1
    history_rewrite_normal_keep_other: int = 0
    history_rewrite_normal_max_chars_per_message: int = 1200
    history_rewrite_heavy_keep_system: int = 1
    history_rewrite_heavy_keep_user: int = 2
    history_rewrite_heavy_keep_assistant: int = 1
    history_rewrite_heavy_keep_tool: int = 2
    history_rewrite_heavy_keep_other: int = 1
    history_rewrite_heavy_max_chars_per_message: int = 1800
    context_budget_enabled: bool = True
    context_budget_response_reserve_ratio: float = 0.3
    context_budget_min_prompt_tokens: int = 512

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Force `.env` values to override process/system environment variables.
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    @property
    def effective_target_base_url(self) -> str | None:
        return self.target_base_url or self.llmapi_base_url

    @property
    def effective_target_api_key(self) -> str | None:
        return self.target_api_key or self.llmapi_api_key


settings = Settings()
