from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str
    content: Any
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    session_id: str = "global"
    temperature: float | None = None
    top_p: float | None = None
    n: int | None = Field(default=1, ge=1)
    stream: bool = False
    stop: str | list[str] | None = None
    max_tokens: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    user: str | None = None
    metadata: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")

    def to_litellm_kwargs(self) -> dict[str, Any]:
        payload = self.model_dump(exclude_none=True)
        return payload


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
