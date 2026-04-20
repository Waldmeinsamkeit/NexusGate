from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import litellm
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from nexusgate.config import settings
from nexusgate.local_proxy import ClientSyncService, LocalKeyManager, SyncStatus
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
    if (
        settings.effective_target_base_url
        and settings.upstream_api_key_required
        and not settings.effective_target_api_key
    ):
        raise RuntimeError("TARGET_API_KEY is required when using third-party upstream base URL.")

    local_key_state = LocalKeyManager(
        configured_key=settings.local_api_key,
        store_path=settings.local_api_key_store_path,
    ).resolve()
    resolved_local_api_key = local_key_state.api_key
    local_key_source = local_key_state.source

    sync_state = SyncStatus(status="disabled", synced_clients=[], errors=[])
    if settings.client_sync_enabled:
        sync_state = ClientSyncService(
            codex_config_path=settings.codex_config_path,
            claude_settings_path=settings.claude_settings_path,
            codex_base_url=settings.codex_local_base_url,
            claude_base_url=settings.claude_local_base_url,
        ).sync_all(resolved_local_api_key)

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
    async def health() -> dict[str, Any]:
        upstream = settings.effective_target_base_url or settings.target_provider
        upstream_mode = "openai_compatible" if settings.effective_target_base_url else "provider_direct"
        auth_mode = "custom_local_api_key" if resolved_local_api_key else (
            "bearer_required" if settings.api_key_required else "disabled"
        )
        return {
            "status": "ok",
            "upstream": upstream,
            "upstream_mode": upstream_mode,
            "auth_mode": auth_mode,
            "local_key_source": local_key_source,
            "sync_status": sync_state.status,
            "synced_clients": sync_state.synced_clients,
            "sync_errors": sync_state.errors,
        }

    def _run_completion(req: ChatCompletionRequest, data: dict[str, Any], background_tasks: BackgroundTasks) -> Any:
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
        return response, req

    @app.post("/v1/chat/completions")
    async def chat_completions(
        request: Request,
        background_tasks: BackgroundTasks,
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None, alias="x-api-key"),
        api_key: str | None = Header(default=None, alias="api-key"),
    ) -> Any:
        auth_value = authorization
        if not auth_value and x_api_key:
            auth_value = f"Bearer {x_api_key}"
        if not auth_value and api_key:
            auth_value = f"Bearer {api_key}"
        _validate_api_key(auth_value, local_api_key=resolved_local_api_key)
        data = await request.json()
        req = ChatCompletionRequest(**data)
        response, req = _run_completion(req=req, data=data, background_tasks=background_tasks)

        if req.stream:
            return StreamingResponse(response, media_type="text/event-stream")
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if isinstance(response, dict):
            return response
        return dict(response)

    @app.post("/v1/responses")
    async def responses_api(
        request: Request,
        background_tasks: BackgroundTasks,
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None, alias="x-api-key"),
        api_key: str | None = Header(default=None, alias="api-key"),
    ) -> Any:
        auth_value = authorization
        if not auth_value and x_api_key:
            auth_value = f"Bearer {x_api_key}"
        if not auth_value and api_key:
            auth_value = f"Bearer {api_key}"
        _validate_api_key(auth_value, local_api_key=resolved_local_api_key)
        data = await request.json()

        # Prefer raw pass-through for Responses API so Codex tool-calling semantics
        # are preserved (editing files, running commands, multi-turn tool loops).
        if settings.effective_target_base_url:
            passthrough = await _passthrough_responses_to_upstream(
                request=request,
                payload=data,
                upstream_base_url=settings.effective_target_base_url,
                upstream_api_key=settings.effective_target_api_key,
            )
            return passthrough

        openai_data = _responses_request_to_openai(data)
        req = ChatCompletionRequest(**openai_data)
        response, req = _run_completion(req=req, data=openai_data, background_tasks=background_tasks)

        if req.stream:
            return StreamingResponse(
                _responses_stream_from_openai(response, model=req.model or settings.target_provider),
                media_type="text/event-stream",
            )

        payload = response.model_dump() if hasattr(response, "model_dump") else (response if isinstance(response, dict) else dict(response))
        return _responses_response_from_openai(payload=payload, model=req.model or settings.target_provider)

    @app.post("/v1/messages")
    async def anthropic_messages(
        request: Request,
        background_tasks: BackgroundTasks,
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None, alias="x-api-key"),
        api_key: str | None = Header(default=None, alias="api-key"),
    ) -> Any:
        auth_value = authorization
        if x_api_key and not auth_value:
            auth_value = f"Bearer {x_api_key}"
        if api_key and not auth_value:
            auth_value = f"Bearer {api_key}"
        _validate_api_key(auth_value, local_api_key=resolved_local_api_key)

        data = await request.json()
        openai_data = _anthropic_request_to_openai(data)
        req = ChatCompletionRequest(**openai_data)
        response, req = _run_completion(req=req, data=openai_data, background_tasks=background_tasks)

        if req.stream:
            return StreamingResponse(
                _anthropic_stream_from_openai(response, model=req.model or settings.target_provider),
                media_type="text/event-stream",
            )

        payload = response.model_dump() if hasattr(response, "model_dump") else (response if isinstance(response, dict) else dict(response))
        return _anthropic_response_from_openai(payload=payload, model=req.model or settings.target_provider)

    return app


def _validate_api_key(authorization: str | None, local_api_key: str | None = None) -> None:
    effective_local_api_key = local_api_key or settings.local_api_key
    if effective_local_api_key:
        token = _extract_auth_token(authorization)
        if token == effective_local_api_key:
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
        )

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


def _extract_auth_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    raw = authorization.strip()
    if not raw:
        return None
    if raw.lower().startswith("bearer "):
        token = raw[7:].strip()
        return token or None
    return raw


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
    if settings.effective_target_base_url:
        kwargs["api_base"] = settings.effective_target_base_url
        if settings.effective_target_api_key:
            kwargs["api_key"] = settings.effective_target_api_key
    return kwargs


def _anthropic_request_to_openai(data: dict[str, Any]) -> dict[str, Any]:
    model = data.get("model") or settings.target_provider
    stream = bool(data.get("stream", False))
    system = data.get("system")
    messages = data.get("messages") or []

    converted: list[dict[str, Any]] = []
    if isinstance(system, str) and system.strip():
        converted.append({"role": "system", "content": system.strip()})
    elif isinstance(system, list):
        system_text = "\n".join(_content_block_to_text(item) for item in system).strip()
        if system_text:
            converted.append({"role": "system", "content": system_text})

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, str):
            converted.append({"role": role, "content": content})
            continue
        if isinstance(content, list):
            text = "\n".join(_content_block_to_text(item) for item in content).strip()
            converted.append({"role": role, "content": text})
            continue
        converted.append({"role": role, "content": json.dumps(content, ensure_ascii=False)})

    payload: dict[str, Any] = {
        "model": model,
        "messages": converted,
        "stream": stream,
        "max_tokens": data.get("max_tokens"),
        "temperature": data.get("temperature"),
        "metadata": data.get("metadata"),
    }
    return {k: v for k, v in payload.items() if v is not None}


def _responses_request_to_openai(data: dict[str, Any]) -> dict[str, Any]:
    model = data.get("model") or settings.target_provider
    stream = bool(data.get("stream", False))
    input_value = data.get("input")
    instructions = data.get("instructions")

    messages: list[dict[str, Any]] = []
    if isinstance(instructions, str) and instructions.strip():
        messages.append({"role": "system", "content": instructions.strip()})

    if isinstance(input_value, str):
        messages.append({"role": "user", "content": input_value})
    elif isinstance(input_value, list):
        for item in input_value:
            role = "user"
            content = ""
            if isinstance(item, dict):
                role = str(item.get("role") or role)
                raw_content = item.get("content")
                if isinstance(raw_content, str):
                    content = raw_content
                elif isinstance(raw_content, list):
                    blocks = []
                    for block in raw_content:
                        if isinstance(block, dict):
                            block_type = block.get("type")
                            if block_type in {"input_text", "output_text", "text"}:
                                blocks.append(str(block.get("text", "")))
                            else:
                                blocks.append(json.dumps(block, ensure_ascii=False))
                        else:
                            blocks.append(str(block))
                    content = "\n".join(blocks).strip()
                elif raw_content is not None:
                    content = json.dumps(raw_content, ensure_ascii=False)
            else:
                content = str(item)
            messages.append({"role": role, "content": content})
    elif input_value is not None:
        messages.append({"role": "user", "content": json.dumps(input_value, ensure_ascii=False)})

    if not messages:
        messages.append({"role": "user", "content": ""})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "max_tokens": data.get("max_output_tokens"),
        "temperature": data.get("temperature"),
        "metadata": data.get("metadata"),
    }
    return {k: v for k, v in payload.items() if v is not None}


def _content_block_to_text(block: Any) -> str:
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        if block.get("type") == "text":
            return str(block.get("text", ""))
        return json.dumps(block, ensure_ascii=False)
    return str(block)


def _anthropic_response_from_openai(payload: dict[str, Any], model: str) -> dict[str, Any]:
    text = _extract_openai_text(payload)
    usage = payload.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    return {
        "id": f"msg_{uuid4().hex}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


def _extract_openai_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                blocks.append(str(item.get("text", "")))
            else:
                blocks.append(json.dumps(item, ensure_ascii=False))
        return "\n".join(blocks).strip()
    return str(content)


def _responses_response_from_openai(payload: dict[str, Any], model: str) -> dict[str, Any]:
    text = _extract_openai_text(payload)
    usage = payload.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))

    return {
        "id": f"resp_{uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": model,
        "output": [
            {
                "id": f"msg_{uuid4().hex}",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                        "annotations": [],
                    }
                ],
            }
        ],
        "output_text": text,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
    }


def _responses_stream_from_openai(response: Any, model: str) -> Iterator[bytes]:
    response_id = f"resp_{uuid4().hex}"
    message_id = f"msg_{uuid4().hex}"
    created_at = int(time.time())
    collected_parts: list[str] = []

    created = {
        "type": "response.created",
        "response": {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "status": "in_progress",
            "model": model,
            "output": [],
        },
    }
    yield _sse_event("response.created", created)
    yield _sse_event(
        "response.in_progress",
        {
            "type": "response.in_progress",
            "response": {
                "id": response_id,
                "object": "response",
                "created_at": created_at,
                "status": "in_progress",
                "model": model,
                "output": [],
            },
        },
    )
    yield _sse_event(
        "response.output_item.added",
        {
            "type": "response.output_item.added",
            "response_id": response_id,
            "output_index": 0,
            "item": {
                "id": message_id,
                "type": "message",
                "status": "in_progress",
                "role": "assistant",
                "content": [],
            },
        },
    )
    yield _sse_event(
        "response.content_part.added",
        {
            "type": "response.content_part.added",
            "response_id": response_id,
            "item_id": message_id,
            "output_index": 0,
            "content_index": 0,
            "part": {"type": "output_text", "text": "", "annotations": []},
        },
    )

    for chunk in response:
        row = chunk.model_dump() if hasattr(chunk, "model_dump") else (chunk if isinstance(chunk, dict) else dict(chunk))
        delta_text = _extract_openai_delta_text(row)
        if not delta_text:
            continue
        collected_parts.append(delta_text)
        yield _sse_event(
            "response.output_text.delta",
            {
                "type": "response.output_text.delta",
                "response_id": response_id,
                "item_id": message_id,
                "output_index": 0,
                "content_index": 0,
                "delta": delta_text,
            },
        )

    full_text = "".join(collected_parts)
    yield _sse_event(
        "response.content_part.done",
        {
            "type": "response.content_part.done",
            "response_id": response_id,
            "item_id": message_id,
            "output_index": 0,
            "content_index": 0,
            "part": {"type": "output_text", "text": full_text, "annotations": []},
        },
    )
    yield _sse_event(
        "response.output_text.done",
        {
            "type": "response.output_text.done",
            "response_id": response_id,
            "item_id": message_id,
            "output_index": 0,
            "content_index": 0,
            "text": full_text,
        },
    )
    yield _sse_event(
        "response.output_item.done",
        {
            "type": "response.output_item.done",
            "response_id": response_id,
            "output_index": 0,
            "item": {
                "id": message_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": full_text,
                        "annotations": [],
                    }
                ],
            },
        },
    )
    completed = {
        "type": "response.completed",
        "response": {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "status": "completed",
            "model": model,
            "output": [
                {
                    "id": message_id,
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": full_text,
                            "annotations": [],
                        }
                    ],
                }
            ],
            "output_text": full_text,
        },
    }
    yield _sse_event("response.completed", completed)
    yield b"data: [DONE]\n\n"


def _extract_openai_delta_text(chunk: dict[str, Any]) -> str:
    choices = chunk.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    content = delta.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(str(item.get("text", "")))
        return "".join(texts)
    return ""


def _anthropic_stream_from_openai(response: Any, model: str) -> Iterator[bytes]:
    message_id = f"msg_{uuid4().hex}"
    start = {
        "type": "message_start",
        "message": {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    }
    yield _sse_event("message_start", start)
    yield _sse_event(
        "content_block_start",
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
    )

    for chunk in response:
        row = chunk.model_dump() if hasattr(chunk, "model_dump") else (chunk if isinstance(chunk, dict) else dict(chunk))
        delta_text = _extract_openai_delta_text(row)
        if delta_text:
            yield _sse_event(
                "content_block_delta",
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": delta_text}},
            )

    yield _sse_event("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield _sse_event("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}})
    yield _sse_event("message_stop", {"type": "message_stop"})


def _sse_event(event: str, payload: dict[str, Any]) -> bytes:
    text = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {text}\n\n".encode("utf-8")


async def _passthrough_responses_to_upstream(
    request: Request,
    payload: dict[str, Any],
    upstream_base_url: str,
    upstream_api_key: str | None,
) -> Any:
    base = upstream_base_url.rstrip("/")
    url = f"{base}/responses"
    headers = _build_upstream_headers(request, upstream_api_key)
    stream = bool(payload.get("stream"))

    if stream:
        async def event_stream() -> Iterator[bytes]:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        detail = body.decode("utf-8", errors="replace")
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Upstream responses stream failed ({resp.status_code}): {detail}",
                        )
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            yield chunk

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream responses failed ({resp.status_code}): {resp.text}",
        )
    try:
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except ValueError:
        return JSONResponse(status_code=resp.status_code, content={"raw": resp.text})


def _build_upstream_headers(request: Request, upstream_api_key: str | None) -> dict[str, str]:
    passthrough_headers = {}
    for key, value in request.headers.items():
        lowered = key.lower()
        if lowered in {"host", "content-length", "authorization"}:
            continue
        passthrough_headers[key] = value

    if upstream_api_key:
        passthrough_headers["Authorization"] = f"Bearer {upstream_api_key}"
    elif "Authorization" not in passthrough_headers:
        passthrough_headers["Authorization"] = ""
    return passthrough_headers
