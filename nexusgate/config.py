from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NexusGate-Core"
    app_env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    request_timeout_seconds: int = 120
    api_key_required: bool = False
    default_model: str = "claude-sonnet-4-5-20250929"
    target_provider: str = "claude-sonnet-4-5-20250929"
    target_base_url: str | None = None
    target_api_key: str | None = None
    compress_threshold: int = 4000
    llmapi_base_url: str | None = None
    llmapi_api_key: str | None = None
    llmapi_model_prefix: str = "llmapi/"
    llmapi_provider_prefix: str = "openai/"
    memory_enabled: bool = True
    memory_store_path: str = Field(default="memory")
    memory_source_root: str = Field(default="F:/repo/GenericAgent")
    memory_collection_name: str = Field(default="nexusgate_memory")
    memory_top_k: int = 6
    memory_use_chroma: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
