from __future__ import annotations

import json

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, status

from nexusgate.config import settings
from nexusgate.gateway import LiteLLMGateway
from nexusgate.memory import MemoryManager
from nexusgate.schemas import ChatCompletionRequest, HealthResponse


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    gateway = LiteLLMGateway(
        timeout_seconds=settings.request_timeout_seconds,
        llmapi_base_url=settings.llmapi_base_url,
        llmapi_api_key=settings.llmapi_api_key,
        llmapi_model_prefix=settings.llmapi_model_prefix,
        llmapi_provider_prefix=settings.llmapi_provider_prefix,
    )
    memory = MemoryManager(
        enabled=settings.memory_enabled,
        store_path=settings.memory_store_path,
        source_root=settings.memory_source_root,
        collection_name=settings.memory_collection_name,
        top_k=settings.memory_top_k,
    )

    @app.get("/health", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name, env=settings.app_env)

    @app.post("/v1/chat/completions")
    def chat_completions(
        request: ChatCompletionRequest,
        background_tasks: BackgroundTasks,
        authorization: str | None = Header(default=None),
    ) -> dict:
        _validate_api_key(authorization)

        raw_messages = [message.model_dump(exclude_none=True) for message in request.messages]
        session_id = _resolve_session_id(request)
        payload = request.to_litellm_kwargs()
        payload["metadata"] = payload.get("metadata") or {}
        payload["metadata"]["session_id"] = session_id
        payload["messages"] = memory.enrich_messages(
            messages=payload["messages"],
            metadata=payload["metadata"],
        )
        if not payload.get("model"):
            payload["model"] = settings.default_model

        try:
            response_payload = gateway.chat_completion(payload)
            final_result = _extract_response_text(response_payload)
            background_tasks.add_task(
                memory.start_memory_update,
                session_id=session_id,
                messages=raw_messages,
                final_result=final_result,
            )
            return response_payload
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream completion failed: {exc}",
            ) from exc

    return app


def _validate_api_key(authorization: str | None) -> None:
    if not settings.api_key_required:
        return
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key.",
    )


def _resolve_session_id(request: ChatCompletionRequest) -> str:
    if request.metadata and request.metadata.get("session_id"):
        return str(request.metadata["session_id"])
    return request.user or "default"


def _extract_response_text(response_payload: dict) -> str:
    try:
        choices = response_payload.get("choices") or []
        message = (choices[0].get("message") or {}) if choices else {}
        content = message.get("content") or ""
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)
    except Exception:
        return ""
