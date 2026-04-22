from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def effective_target_base_url(self) -> str | None:
        return self.target_base_url or self.llmapi_base_url

    @property
    def effective_target_api_key(self) -> str | None:
        return self.target_api_key or self.llmapi_api_key


settings = Settings()
