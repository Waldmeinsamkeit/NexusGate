from __future__ import annotations

import json
from typing import Any

import litellm
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from nexusgate.config import settings
from nexusgate.memory import MemoryManager
from nexusgate.schemas import ChatCompletionRequest

try:
    from llmlingua import PromptCompressor
except ImportError:  # pragma: no cover
    PromptCompressor = None


L0_META_RULES = (
    "你是由 NexusGate-Core 增强的智能助手。"
    "始终基于 <nexus_context> 事实回答，若未提及则明确说“不知道”。"
)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.2.0")
    memory = MemoryManager(
        enabled=settings.memory_enabled,
        store_path=settings.memory_store_path,
        source_root=settings.memory_source_root,
        collection_name=settings.memory_collection_name,
        top_k=settings.memory_top_k,
        use_chroma=settings.memory_use_chroma,
    )
    compressor = None
    if PromptCompressor is not None:
        try:
            compressor = PromptCompressor(
                model_name=settings.llmlingua_model_name,
                use_llmlingua2=settings.llmlingua_use_llmlingua2,
            )
        except TypeError:
            compressor = PromptCompressor(model_name=settings.llmlingua_model_name)
        except Exception:
            compressor = None

    @app.get("/health")
    async def health() -> dict[str, str]:
        upstream = settings.target_base_url or settings.target_provider
        return {"status": "ok", "upstream": upstream}

    @app.post("/v1/chat/completions")
    async def chat_completions(
        request: Request,
        background_tasks: BackgroundTasks,
        authorization: str | None = Header(default=None),
    ) -> Any:
        _validate_api_key(authorization)
        data = await request.json()
        req = ChatCompletionRequest(**data)
        session_id = _resolve_session_id(req)
        user_query = _extract_latest_user_query(req.messages)

        memory_context = memory.get_memory(session_id, user_query)
        enhanced_messages = [
            {"role": "system", "content": L0_META_RULES},
            {"role": "system", "content": f"<nexus_context>\n{memory_context}\n</nexus_context>"},
            *[message.model_dump(exclude_none=True) for message in req.messages],
        ]

        if _should_compress(req=req, messages=enhanced_messages):
            compressed = _compress_text(compressor, enhanced_messages)
            if compressed:
                enhanced_messages = [
                    {"role": "system", "content": L0_META_RULES},
                    {"role": "system", "content": f"<nexus_context>\n{compressed}\n</nexus_context>"},
                    *[message.model_dump(exclude_none=True) for message in req.messages[-3:]],
                ]

        kwargs = _build_upstream_kwargs(req=req, data=data, enhanced_messages=enhanced_messages)

        try:
            response = litellm.completion(**kwargs)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream completion failed: {exc}",
            ) from exc

        raw_messages = [message.model_dump(exclude_none=True) for message in req.messages]
        background_tasks.add_task(memory.distill_to_l4, session_id, raw_messages)

        if req.stream:
            return StreamingResponse(response, media_type="text/event-stream")
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if isinstance(response, dict):
            return response
        return dict(response)

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


def _resolve_session_id(req: ChatCompletionRequest) -> str:
    if req.session_id:
        return req.session_id
    if req.metadata and req.metadata.get("session_id"):
        return str(req.metadata["session_id"])
    return req.user or "global"


def _extract_latest_user_query(messages: list[Any]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        if isinstance(message.content, str):
            return message.content
        return json.dumps(message.content, ensure_ascii=False)
    return ""


def _should_compress(req: ChatCompletionRequest, messages: list[dict[str, Any]]) -> bool:
    full_text = "\n".join(_message_content_text(msg) for msg in messages)
    model = req.model or settings.target_provider
    try:
        token_count = litellm.token_counter(model=model, text=full_text)
    except Exception:
        return False
    return token_count > settings.compress_threshold


def _compress_text(compressor: Any, messages: list[dict[str, Any]]) -> str | None:
    if compressor is None:
        return None
    full_text = "\n".join(_message_content_text(msg) for msg in messages)
    try:
        compressed = compressor.compress(
            full_text,
            rate=settings.llmlingua_compress_rate,
            preserve=["system", "question"],
        )
        if isinstance(compressed, dict):
            return str(compressed.get("compressed_prompt") or compressed.get("text") or "")
        return str(compressed)
    except Exception:
        return None


def _message_content_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _build_upstream_kwargs(
    req: ChatCompletionRequest,
    data: dict[str, Any],
    enhanced_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    passthrough = {
        key: value
        for key, value in data.items()
        if key not in {"messages", "session_id", "model"}
    }
    kwargs: dict[str, Any] = {
        "model": req.model or settings.target_provider,
        "messages": enhanced_messages,
        "stream": req.stream,
        "temperature": req.temperature if req.temperature is not None else 0.7,
        **passthrough,
    }
    if settings.target_base_url:
        kwargs["api_base"] = settings.target_base_url
        if settings.target_api_key:
            kwargs["api_key"] = settings.target_api_key
    return kwargs
