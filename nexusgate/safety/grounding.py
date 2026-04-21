from __future__ import annotations

import re
from typing import Any


def split_claims(text: str) -> list[str]:
    stripped = (text or "").strip()
    if not stripped:
        return []
    parts = re.split(r"[。！？!?;\n]+", stripped)
    return [part.strip() for part in parts if part.strip()]


def supported_claim_check(answer_text: str, sources: list[str]) -> dict[str, Any]:
    claims = split_claims(answer_text)
    if not claims:
        return {"claims": [], "unsupported_claims": [], "unsupported_ratio": 0.0}

    source_blob = " ".join(item.lower() for item in sources if item).strip()
    unsupported: list[str] = []
    for claim in claims:
        tokens = [token for token in re.findall(r"[a-z0-9_\-/\.]{3,}|[\u4e00-\u9fff]{2,}", claim.lower()) if token]
        if not tokens:
            continue
        hits = sum(1 for token in tokens if token in source_blob)
        if hits == 0:
            unsupported.append(claim)
    ratio = float(len(unsupported)) / float(max(len(claims), 1))
    return {"claims": claims, "unsupported_claims": unsupported, "unsupported_ratio": ratio}


def apply_hallucination_guard(answer_text: str, check: dict[str, Any], strict: bool = False) -> str:
    unsupported = check.get("unsupported_claims") or []
    if not unsupported:
        return answer_text
    if strict or float(check.get("unsupported_ratio") or 0.0) >= 0.5:
        return f"{answer_text}\n\n注：上述部分结论未在当前记忆或输入中找到依据。"
    return answer_text

