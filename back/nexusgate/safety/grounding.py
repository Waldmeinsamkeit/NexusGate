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
        supported = bool(hits) and not numeric_mismatch
        critical = _is_critical_fact(claim) and claim_kind == "fact"
        reason = "" if supported else ("numeric_mismatch" if numeric_mismatch else "token_missing")

        row = {
            "claim_id": claim_id,
            "text": claim,
            "claim_type": claim_kind,
            "supported": supported,
            "supported_by": hits[:8],
            "unsupported_reason": reason,
            "critical": critical,
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
