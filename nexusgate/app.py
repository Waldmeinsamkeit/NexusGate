from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import litellm
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from nexusgate.config import settings
from nexusgate.gateway import route
from nexusgate.local_proxy import ClientSyncService, LocalKeyManager, SyncStatus
from nexusgate.memory import MemoryManager
from nexusgate.router import ProviderRouter
from nexusgate.safety import apply_hallucination_guard, supported_claim_check
from nexusgate.schemas import ChatCompletionRequest, NormalizedRequest


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
    provider_router = ProviderRouter()

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

    def _run_completion(
        req: ChatCompletionRequest,
        data: dict[str, Any],
        normalized_req: NormalizedRequest,
        background_tasks: BackgroundTasks,
    ) -> Any:
        session_id = normalized_req.session_id
        user_query = normalized_req.user_text

        memory_pack = memory.build_memory_pack(session_id, user_query)
        decision = route(
            normalized_req=normalized_req,
            defaults={
                "model": req.model or settings.target_provider,
                "api_base": settings.effective_target_base_url,
                "api_key": settings.effective_target_api_key,
            },
            memory_pack_size=_estimate_pack_size(memory_pack),
            pack_features=memory_pack.pack_features,
            risk_profile=memory_pack.risk_profile,
            router=provider_router,
        )
        enriched_messages, memory_pack = memory.enrich_from_normalized_request(
            normalized_req=normalized_req,
            provider_style=str(decision.get("render_mode") or "openai"),
            memory_pack=memory_pack,
        )
        memory_context = memory.render_memory_for_provider(
            pack=memory_pack,
            provider_style=str(decision.get("render_mode") or "openai"),
        )
        grounding_mode = str(decision.get("grounding_mode") or "balanced")
        grounding_rules = _build_grounding_system_rules(grounding_mode=grounding_mode)
        citation_block = _build_citation_system_block(memory_pack.citations)
        enhanced_messages = [
            {"role": "system", "content": L0_META_RULES},
            {"role": "system", "content": grounding_rules},
            {"role": "system", "content": citation_block},
            *enriched_messages,
        ]

        kwargs = _build_upstream_kwargs(req=req, data=data, enhanced_messages=enhanced_messages)
        if decision.get("api_base"):
            kwargs["api_base"] = decision["api_base"]
        if decision.get("api_key"):
            kwargs["api_key"] = decision["api_key"]
        if settings.effective_target_base_url and not kwargs.get("custom_llm_provider"):
            kwargs["custom_llm_provider"] = "openai"
        explicit_model_requested = bool((req.model or "").strip())
        attempt_models = [str(decision["model"])]
        if not explicit_model_requested:
            fallback_chain = decision.get("fallback_chain") or decision.get("fallbacks") or []
            attempt_models.extend(str(item) for item in fallback_chain)
        deduped_models: list[str] = []
        for model in attempt_models:
            if model and model not in deduped_models:
                deduped_models.append(model)
        response = None
        last_error: Exception | None = None
        fallback_events: list[dict[str, Any]] = []
        for model in deduped_models:
            kwargs["model"] = _normalize_model_for_openai_compatible(
                model=model,
                openai_compatible=bool(settings.effective_target_base_url),
            )
            current_messages = kwargs.get("messages") or []
            for retry_index in range(2):
                started = time.perf_counter()
                try:
                    kwargs["messages"] = current_messages
                    response = litellm.completion(**kwargs)
                    provider_router.health.record_success(
                        provider=_provider_from_model(model, fallback=str(decision.get("provider") or "openai")),
                        latency_ms=(time.perf_counter() - started) * 1000.0,
                    )
                    break
                except Exception as exc:
                    provider_router.health.record_failure(
                        provider=_provider_from_model(model, fallback=str(decision.get("provider") or "openai"))
                    )
                    failure_mode = _classify_upstream_failure(exc)
                    fallback_events.append(
                        {
                            "model": model,
                            "mode": failure_mode,
                            "retry_index": retry_index,
                            "error": str(exc)[:280],
                        }
                    )
                    last_error = exc
                    # Context overflow fallback: keep canonical pack, trim render and retry once.
                    if failure_mode == "context_overflow" and retry_index == 0:
                        current_messages = _trim_messages_for_context_overflow(current_messages)
                        continue
                    break
            if response is not None:
                break
        if response is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream completion failed after fallbacks: {last_error}",
            ) from last_error

        raw_messages = [message.model_dump(exclude_none=True) for message in normalized_req.messages]
        background_tasks.add_task(memory.distill_to_l4, session_id, raw_messages)
        safety_ctx = {
            "session_id": session_id,
            "memory_context": memory_context,
            "user_text": user_query,
            "metadata": normalized_req.metadata or {},
            "citations": memory_pack.citations,
            "trace": {
                "retrieval": memory_pack.retrieval_trace,
                "assembly": memory_pack.assembly_trace,
                "routing": {
                    "provider": decision.get("provider"),
                    "model": decision.get("model"),
                    "reason_codes": decision.get("reason_codes") or [],
                    "fallback_chain": decision.get("fallback_chain") or decision.get("fallbacks") or [],
                    "context_budget": decision.get("context_budget"),
                    "grounding_mode": decision.get("grounding_mode"),
                },
                "render": memory_pack.trim_report,
                "fallback": fallback_events,
            },
        }
        return response, req, safety_ctx

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
        normalized_req = _normalize_chat_request(data=data, req=req)
        response, req, safety_ctx = _run_completion(
            req=req,
            data=data,
            normalized_req=normalized_req,
            background_tasks=background_tasks,
        )

        if req.stream:
            return StreamingResponse(response, media_type="text/event-stream")
        payload = response.model_dump() if hasattr(response, "model_dump") else (response if isinstance(response, dict) else dict(response))
        return _apply_grounding_to_openai_payload(payload=payload, safety_ctx=safety_ctx)

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
        openai_data = _responses_request_to_openai(data)
        req = ChatCompletionRequest(**openai_data)
        normalized_req = _normalize_responses_request(data=data, req=req)
        session_id = normalized_req.session_id
        raw_messages = [message.model_dump(exclude_none=True) for message in normalized_req.messages]

        # Prefer raw pass-through for Responses API so Codex tool-calling semantics
        # are preserved (editing files, running commands, multi-turn tool loops).
        if settings.effective_target_base_url:
            passthrough = await _passthrough_responses_to_upstream(
                request=request,
                payload=data,
                upstream_base_url=settings.effective_target_base_url,
                upstream_api_key=settings.effective_target_api_key,
                on_complete=lambda text: memory.start_memory_update(
                    session_id=session_id,
                    messages=raw_messages,
                    final_result=text or "stream_completed",
                ),
            )
            return passthrough

        response, req, safety_ctx = _run_completion(
            req=req,
            data=openai_data,
            normalized_req=normalized_req,
            background_tasks=background_tasks,
        )

        if req.stream:
            return StreamingResponse(
                _responses_stream_from_openai(response, model=req.model or settings.target_provider),
                media_type="text/event-stream",
            )

        payload = response.model_dump() if hasattr(response, "model_dump") else (response if isinstance(response, dict) else dict(response))
        payload = _apply_grounding_to_openai_payload(payload=payload, safety_ctx=safety_ctx)
        background_tasks.add_task(
            memory.start_memory_update,
            session_id,
            raw_messages,
            _responses_response_output_text(payload),
        )
        return _responses_response_from_openai(
            payload=payload,
            model=req.model or settings.target_provider,
            citations=safety_ctx.get("citations") or [],
            grounding=safety_ctx.get("grounding") or {},
            trace=safety_ctx.get("trace") or {},
        )

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
        normalized_req = _normalize_messages_request(data=data, req=req)
        response, req, safety_ctx = _run_completion(
            req=req,
            data=openai_data,
            normalized_req=normalized_req,
            background_tasks=background_tasks,
        )

        if req.stream:
            return StreamingResponse(
                _anthropic_stream_from_openai(response, model=req.model or settings.target_provider),
                media_type="text/event-stream",
            )

        payload = response.model_dump() if hasattr(response, "model_dump") else (response if isinstance(response, dict) else dict(response))
        payload = _apply_grounding_to_openai_payload(payload=payload, safety_ctx=safety_ctx)
        return _anthropic_response_from_openai(
            payload=payload,
            model=req.model or settings.target_provider,
            citations=safety_ctx.get("citations") or [],
            grounding=safety_ctx.get("grounding") or {},
            trace=safety_ctx.get("trace") or {},
        )

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
    if req.session_id and req.session_id != "global":
        return req.session_id
    if req.metadata and req.metadata.get("session_id"):
        return str(req.metadata["session_id"])
    if req.session_id:
        return req.session_id
    return req.user or "global"


def _normalize_chat_request(data: dict[str, Any], req: ChatCompletionRequest) -> NormalizedRequest:
    return NormalizedRequest(
        api_style="chat_completions",
        session_id=_resolve_session_id(req),
        user_text=_extract_latest_user_query(req.messages),
        messages=req.messages,
        requested_model=req.model or "auto",
        metadata=req.metadata or {},
        stream=bool(req.stream),
        tool_required=bool(data.get("tools")),
        response_mode="chat",
    )


def _normalize_responses_request(data: dict[str, Any], req: ChatCompletionRequest) -> NormalizedRequest:
    return NormalizedRequest(
        api_style="responses",
        session_id=_resolve_session_id(req),
        user_text=_extract_latest_user_query(req.messages),
        messages=req.messages,
        requested_model=req.model or "auto",
        metadata=req.metadata or {},
        stream=bool(req.stream),
        tool_required=bool(data.get("tools")),
        response_mode="responses",
    )


def _normalize_messages_request(data: dict[str, Any], req: ChatCompletionRequest) -> NormalizedRequest:
    return NormalizedRequest(
        api_style="messages",
        session_id=_resolve_session_id(req),
        user_text=_extract_latest_user_query(req.messages),
        messages=req.messages,
        requested_model=req.model or "auto",
        metadata=req.metadata or {},
        stream=bool(req.stream),
        tool_required=bool(data.get("tools")),
        response_mode="messages",
    )


def _extract_latest_user_query(messages: list[Any]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        if isinstance(message.content, str):
            return message.content
        return json.dumps(message.content, ensure_ascii=False)
    return ""


def _estimate_pack_size(pack: Any) -> int:
    parts = [
        str(getattr(pack, "l0", "")),
        str(getattr(pack, "l1", "")),
        str(getattr(pack, "l2", "")),
        str(getattr(pack, "l3", "")),
        str(getattr(pack, "l4", "")),
    ]
    return sum(len(part) for part in parts)


def _provider_from_model(model: str, fallback: str = "openai") -> str:
    lowered = (model or "").lower()
    if "claude" in lowered or lowered.startswith("anthropic/"):
        return "anthropic"
    if lowered.startswith("openai/") or lowered.startswith("gpt-"):
        return "openai"
    return fallback


def _normalize_model_for_openai_compatible(model: str, openai_compatible: bool) -> str:
    if not openai_compatible:
        return model
    lowered = (model or "").strip()
    if lowered.lower().startswith("openai/"):
        return lowered.split("/", 1)[1]
    return lowered


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


def _build_grounding_system_rules(grounding_mode: str) -> str:
    if grounding_mode == "strict":
        return (
            "Grounding mode: strict. Use only user input and cited memory facts. "
            "If evidence is missing, say you do not know. Do not invent ports, paths, keys, or config values."
        )
    if grounding_mode == "relaxed":
        return "Grounding mode: relaxed. Prefer cited memory, but reasonable inference is allowed when uncertainty is explicit."
    return "Grounding mode: balanced. Prefer cited memory and clearly mark uncertainty when evidence is weak."


def _build_citation_system_block(citations: list[dict[str, Any]]) -> str:
    if not citations:
        return "Citation refs: none"
    rows = []
    for row in citations[:6]:
        ref = str(row.get("memory_ref") or "memory")
        snippet = str(row.get("snippet") or "")[:120]
        rows.append(f"- {ref}: {snippet}")
    return "Citation refs:\n" + "\n".join(rows)


def _classify_upstream_failure(exc: Exception) -> str:
    lowered = str(exc).lower()
    if any(token in lowered for token in ("context_length", "context window", "maximum context", "too many tokens")):
        return "context_overflow"
    if any(token in lowered for token in ("tool", "function call", "does not support tools")):
        return "tool_capability"
    if any(token in lowered for token in ("timeout", "connection", "429", "503", "502", "service unavailable")):
        return "provider_failure"
    return "unknown"


def _trim_messages_for_context_overflow(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    for row in messages:
        patched = dict(row)
        if patched.get("role") == "system" and "<nexus_context>" in str(patched.get("content") or ""):
            content = str(patched.get("content") or "")
            keep = max(len(content) // 2, 600)
            patched["content"] = content[:keep]
        trimmed.append(patched)
    return trimmed


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


def _anthropic_response_from_openai(
    payload: dict[str, Any],
    model: str,
    citations: list[dict[str, Any]] | None = None,
    grounding: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "citations": citations or [],
        "grounding": grounding or {},
        "trace": trace or {},
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


def _apply_grounding_to_openai_payload(payload: dict[str, Any], safety_ctx: dict[str, Any]) -> dict[str, Any]:
    text = _extract_openai_text(payload)
    source_blobs = [
        str(safety_ctx.get("user_text") or ""),
        str(safety_ctx.get("memory_context") or ""),
    ]
    check = supported_claim_check(answer_text=text, sources=source_blobs)
    strict = _is_high_risk_metadata(safety_ctx.get("metadata") or {})
    grounded_text = apply_hallucination_guard(answer_text=text, check=check, strict=strict)
    if bool(check.get("has_critical_unsupported")):
        grounded_text = _degrade_critical_unsupported_claims(text=grounded_text, check=check)
        safety_ctx.setdefault("trace", {}).setdefault("grounding", {})["action"] = "critical_degraded_template"
    else:
        safety_ctx.setdefault("trace", {}).setdefault("grounding", {})["action"] = "pass_through_or_warning"
    safety_ctx["grounding"] = check
    safety_ctx.setdefault("trace", {}).setdefault("grounding", {}).update(
        {
            "claim_count": len(check.get("claims") or []),
            "unsupported_ratio": float(check.get("unsupported_ratio") or 0.0),
            "critical_unsupported_count": len(check.get("critical_unsupported_claims") or []),
        }
    )
    if grounded_text == text:
        patched = dict(payload)
        patched["nexus_trace"] = safety_ctx.get("trace") or {}
        return patched
    patched = dict(payload)
    choices = patched.get("choices") or []
    if not choices:
        return patched
    first = dict(choices[0])
    message = dict(first.get("message") or {})
    message["content"] = grounded_text
    first["message"] = message
    choices = list(choices)
    choices[0] = first
    patched["choices"] = choices
    patched["nexus_trace"] = safety_ctx.get("trace") or {}
    return patched


def _is_high_risk_metadata(metadata: dict[str, Any]) -> bool:
    risk_level = str(metadata.get("risk_level") or "").lower()
    if risk_level in {"high", "critical"}:
        return True
    task_type = str(metadata.get("task_type") or "").lower()
    return task_type in {"debug", "compliance", "medical", "legal", "finance"}


def _degrade_critical_unsupported_claims(text: str, check: dict[str, Any]) -> str:
    critical_claims = [str(item).strip() for item in (check.get("critical_unsupported_claims") or []) if str(item).strip()]
    if not critical_claims:
        return text
    degraded = text
    for claim in critical_claims:
        degraded = degraded.replace(claim, "")
    degraded = re.sub(r"\n{3,}", "\n\n", degraded).strip()
    if not degraded:
        degraded = "I do not have enough grounded evidence to answer this reliably."
    return f"{degraded}\n\nNote: Critical claims without evidence were removed."


def _responses_response_from_openai(
    payload: dict[str, Any],
    model: str,
    citations: list[dict[str, Any]] | None = None,
    grounding: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "citations": citations or [],
        "grounding": grounding or {},
        "trace": trace or {},
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
    on_complete: Any = None,
) -> Any:
    base = upstream_base_url.rstrip("/")
    url = f"{base}/responses"
    headers = _build_upstream_headers(request, upstream_api_key)
    stream = bool(payload.get("stream"))

    if stream:
        async def event_stream() -> Iterator[bytes]:
            buffer = ""
            parts: list[str] = []
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
                            text = chunk.decode("utf-8", errors="ignore")
                            buffer += text
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if not line.startswith("data: "):
                                    continue
                                raw = line[6:].strip()
                                if not raw or raw == "[DONE]":
                                    continue
                                try:
                                    obj = json.loads(raw)
                                except Exception:
                                    continue
                                event_type = obj.get("type")
                                if event_type == "response.output_text.delta":
                                    delta = obj.get("delta")
                                    if isinstance(delta, str):
                                        parts.append(delta)
                                elif event_type == "response.output_text.done":
                                    done_text = obj.get("text")
                                    if isinstance(done_text, str):
                                        parts = [done_text]
                            yield chunk
            if on_complete is not None:
                final_text = "".join(parts).strip()
                on_complete(final_text)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream responses failed ({resp.status_code}): {resp.text}",
        )
    try:
        body = resp.json()
        if on_complete is not None:
            on_complete(_responses_response_output_text(body))
        return JSONResponse(status_code=resp.status_code, content=body)
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


def _responses_response_output_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = payload.get("output")
    if not isinstance(output, list):
        return ""

    collected: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    collected.append(text)
    return "".join(collected).strip()
