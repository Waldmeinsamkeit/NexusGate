from __future__ import annotations

import re
from typing import Any


def split_claims(text: str) -> list[str]:
    stripped = (text or "").strip()
    if not stripped:
        return []
    parts = re.split(r"[。！？!?;\n]+", stripped)
    return [part.strip() for part in parts if part.strip()]


def _claim_type(claim: str) -> str:
    lowered = (claim or "").lower()
    if any(token in lowered for token in ("must", "should", "建议", "recommend", "可以", "try")):
        return "suggestion"
    if any(token in lowered for token in ("maybe", "可能", "seems", "推测", "猜")):
        return "inference"
    return "fact"


def _is_critical_fact(claim: str) -> bool:
    lowered = (claim or "").lower()
    critical_tokens = (
        "port",
        "api",
        "key",
        "token",
        "path",
        "config",
        "url",
        "endpoint",
        "版本",
        "配置",
        "端口",
        "密钥",
    )
    return any(token in lowered for token in critical_tokens)


def _tokenize(claim: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9_\-/\.]{3,}|[\u4e00-\u9fff]{2,}", claim.lower()) if token]


def _split_source_spans(sources: list[str]) -> list[str]:
    spans: list[str] = []
    for src in sources:
        text = (src or "").strip()
        if not text:
            continue
        parts = re.split(r"[。！？!?;\n]+", text)
        spans.extend(part.strip() for part in parts if part.strip())
    return spans


def _extract_entities(claim: str) -> list[tuple[str, str]]:
    text = (claim or "").strip()
    entities: list[tuple[str, str]] = []
    kv_pattern = re.compile(
        r"([a-zA-Z_][\w\-\.\/]{1,40}|[\u4e00-\u9fff]{2,8})\s*(?:[:=]|是|为)\s*([a-zA-Z0-9_/\.\-]{1,80}|\d+)",
        re.I,
    )
    for match in kv_pattern.finditer(text):
        key = (match.group(1) or "").strip().lower()
        value = (match.group(2) or "").strip().lower()
        if key and value:
            entities.append((key, value))

    lowered = text.lower()
    number_matches = re.findall(r"\d+", lowered)
    key_aliases = {
        "port": ("port", "端口"),
        "path": ("path", "路径"),
        "url": ("url", "endpoint", "接口"),
        "version": ("version", "版本"),
        "token": ("token", "key", "密钥"),
    }
    for canonical, aliases in key_aliases.items():
        if any(alias in lowered for alias in aliases):
            for number in number_matches[:2]:
                entities.append((canonical, number))
    return entities


def _entity_supported(entity: tuple[str, str], spans: list[str]) -> bool:
    key, value = entity
    key_l = key.lower()
    value_l = value.lower()
    for span in spans:
        lowered = span.lower()
        if key_l not in lowered or value_l not in lowered:
            continue
        pattern = rf"{re.escape(key_l)}\s*(?:[:=]|是|为)\s*{re.escape(value_l)}"
        if re.search(pattern, lowered, re.I):
            return True
    return False


def _ngrams(tokens: list[str], n: int) -> set[str]:
    if len(tokens) < n:
        return set(tokens)
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _best_ngram_overlap_ratio(claim: str, spans: list[str]) -> float:
    claim_tokens = _tokenize(claim)
    if not claim_tokens:
        return 0.0
    claim_unigrams = set(claim_tokens)
    claim_bigrams = _ngrams(claim_tokens, 2)
    best = 0.0
    for span in spans:
        span_tokens = _tokenize(span)
        if not span_tokens:
            continue
        span_unigrams = set(span_tokens)
        span_bigrams = _ngrams(span_tokens, 2)
        uni_overlap = len(claim_unigrams & span_unigrams) / float(max(len(claim_unigrams), 1))
        bi_overlap = len(claim_bigrams & span_bigrams) / float(max(len(claim_bigrams), 1))
        score = (uni_overlap * 0.6) + (bi_overlap * 0.4)
        if score > best:
            best = score
    return best


def _decide_degrade_action(*, unsupported_ratio: float, has_critical_unsupported: bool, strict: bool) -> str:
    if has_critical_unsupported and strict:
        return "retry_with_stricter_grounding"
    if has_critical_unsupported:
        return "strip_unsupported"
    if unsupported_ratio <= 0.0:
        return "pass_through"
    if strict or unsupported_ratio >= 0.5:
        return "degrade_uncertainty"
    return "attach_warning"


def supported_claim_check(answer_text: str, sources: list[str], *, strict: bool = False) -> dict[str, Any]:
    claim_texts = split_claims(answer_text)
    if not claim_texts:
        return {
            "claims": [],
            "claim_types": [],
            "supported_claim_ids": [],
            "unsupported_claim_ids": [],
            "critical_unsupported_claim_ids": [],
            "unsupported_claims": [],
            "unsupported_ratio": 0.0,
            "critical_unsupported_claims": [],
            "has_critical_unsupported": False,
            "degrade_action": "pass_through",
        }

    source_blob = " ".join(item.lower() for item in sources if item).strip()
    source_spans = _split_source_spans(sources)
    claims: list[dict[str, Any]] = []
    supported_claim_ids: list[str] = []
    unsupported_claim_ids: list[str] = []
    critical_unsupported_claim_ids: list[str] = []
    unsupported_claims: list[str] = []

    for idx, claim in enumerate(claim_texts, start=1):
        claim_id = f"c{idx}"
        claim_kind = _claim_type(claim)
        tokens = _tokenize(claim)
        hits = [token for token in tokens if token in source_blob]
        numbers = re.findall(r"\d+", claim)
        numeric_mismatch = bool(numbers) and not all(number in source_blob for number in numbers)
        entities = _extract_entities(claim)
        entity_missing = [f"{key}={value}" for (key, value) in entities if not _entity_supported((key, value), source_spans)]
        overlap_ratio = _best_ngram_overlap_ratio(claim, source_spans)
        overlap_threshold = 0.58 if strict else 0.42
        supported = not numeric_mismatch and not entity_missing and (overlap_ratio >= overlap_threshold or bool(hits))
        critical = _is_critical_fact(claim) and claim_kind == "fact"
        reason = ""
        if not supported:
            if numeric_mismatch:
                reason = "numeric_mismatch"
            elif entity_missing:
                reason = "entity_mismatch"
            else:
                reason = "semantic_mismatch"

        row = {
            "claim_id": claim_id,
            "text": claim,
            "claim_type": claim_kind,
            "supported": supported,
            "supported_by": hits[:8],
            "unsupported_reason": reason,
            "critical": critical,
            "semantic_overlap_ratio": round(overlap_ratio, 4),
            "entity_checks": [f"{key}={value}" for key, value in entities],
            "missing_entities": entity_missing,
        }
        claims.append(row)

        if supported:
            supported_claim_ids.append(claim_id)
            continue

        unsupported_claim_ids.append(claim_id)
        unsupported_claims.append(claim)
        if critical:
            critical_unsupported_claim_ids.append(claim_id)

    unsupported_ratio = float(len(unsupported_claim_ids)) / float(max(len(claims), 1))
    critical_unsupported_claims = [
        row["text"] for row in claims if row["claim_id"] in set(critical_unsupported_claim_ids)
    ]
    degrade_action = _decide_degrade_action(
        unsupported_ratio=unsupported_ratio,
        has_critical_unsupported=bool(critical_unsupported_claim_ids),
        strict=strict,
    )

    return {
        "claims": claims,
        "claim_types": [{"claim_id": row["claim_id"], "type": row["claim_type"]} for row in claims],
        "supported_claim_ids": supported_claim_ids,
        "unsupported_claim_ids": unsupported_claim_ids,
        "critical_unsupported_claim_ids": critical_unsupported_claim_ids,
        "unsupported_claims": unsupported_claims,
        "unsupported_ratio": unsupported_ratio,
        "critical_unsupported_claims": critical_unsupported_claims,
        "has_critical_unsupported": bool(critical_unsupported_claim_ids),
        "degrade_action": degrade_action,
    }


def apply_hallucination_guard(answer_text: str, check: dict[str, Any], strict: bool = False) -> str:
    action = str(check.get("degrade_action") or "")
    if not action:
        action = _decide_degrade_action(
            unsupported_ratio=float(check.get("unsupported_ratio") or 0.0),
            has_critical_unsupported=bool(check.get("has_critical_unsupported")),
            strict=strict,
        )

    if action == "pass_through":
        return answer_text
    if action == "attach_warning":
        return f"{answer_text}\n\nWarning: Some details are weakly grounded in the provided evidence."
    if action == "degrade_uncertainty":
        return f"{answer_text}\n\nNote: This answer may be incomplete because evidence is limited."
    if action == "strip_unsupported":
        degraded = answer_text
        for claim in check.get("unsupported_claims") or []:
            degraded = degraded.replace(str(claim), "")
        degraded = re.sub(r"\n{3,}", "\n\n", degraded).strip()
        if not degraded:
            degraded = "I do not have enough grounded evidence to answer this reliably."
        return f"{degraded}\n\nNote: Unsupported claims were removed."
    if action == "retry_with_stricter_grounding":
        return f"{answer_text}\n\nNote: Critical claims require stricter grounding validation."
    return answer_text
