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


def supported_claim_check(answer_text: str, sources: list[str]) -> dict[str, Any]:
    claims = split_claims(answer_text)
    if not claims:
        return {
            "claims": [],
            "claim_types": [],
            "unsupported_claims": [],
            "unsupported_ratio": 0.0,
            "critical_unsupported_claims": [],
            "has_critical_unsupported": False,
        }

    source_blob = " ".join(item.lower() for item in sources if item).strip()
    unsupported: list[str] = []
    claim_types: list[dict[str, str]] = []
    for claim in claims:
        claim_kind = _claim_type(claim)
        claim_types.append({"claim": claim, "type": claim_kind})
        tokens = [token for token in re.findall(r"[a-z0-9_\-/\.]{3,}|[\u4e00-\u9fff]{2,}", claim.lower()) if token]
        if not tokens:
            continue
        hits = sum(1 for token in tokens if token in source_blob)
        claim_numbers = re.findall(r"\d+", claim)
        numeric_mismatch = bool(claim_numbers) and not all(number in source_blob for number in claim_numbers)
        if hits == 0 or numeric_mismatch:
            unsupported.append(claim)
    ratio = float(len(unsupported)) / float(max(len(claims), 1))
    critical_unsupported = [claim for claim in unsupported if _is_critical_fact(claim)]
    return {
        "claims": claims,
        "claim_types": claim_types,
        "unsupported_claims": unsupported,
        "unsupported_ratio": ratio,
        "critical_unsupported_claims": critical_unsupported,
        "has_critical_unsupported": bool(critical_unsupported),
    }


def apply_hallucination_guard(answer_text: str, check: dict[str, Any], strict: bool = False) -> str:
    unsupported = check.get("unsupported_claims") or []
    if not unsupported:
        return answer_text
    if strict or bool(check.get("has_critical_unsupported")) or float(check.get("unsupported_ratio") or 0.0) >= 0.5:
        return f"{answer_text}\n\nNote: Some claims are not grounded in the provided input/memory."
    return answer_text
