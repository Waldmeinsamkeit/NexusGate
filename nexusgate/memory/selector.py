from __future__ import annotations

import re

from nexusgate.memory.models import LayerBudgets, MemoryContext, MemoryItem
from nexusgate.memory.policies import (
    CODING_HINTS,
    DEBUG_HINTS,
    PLANNING_HINTS,
    RECALL_HINTS,
    budget_for_task as policy_budget_for_task,
)
from nexusgate.memory.scoring import dedupe_items, rank_items, score_items


class MemorySelector:
    def __init__(self, budgets: LayerBudgets | None = None) -> None:
        self.budgets = budgets or LayerBudgets()

    def classify_task(self, user_text: str) -> str:
        text = (user_text or "").lower()
        if self._contains_any(text, DEBUG_HINTS):
            return "debug"
        if self._contains_any(text, CODING_HINTS):
            return "coding"
        if self._contains_any(text, PLANNING_HINTS):
            return "planning"
        if self._contains_any(text, RECALL_HINTS):
            return "retrieval-only"
        return "chat"

    def budget_for_task(self, task_type: str) -> dict[str, int]:
        return policy_budget_for_task(task_type, self.budgets)

    def select(
        self,
        *,
        user_text: str,
        l0: str,
        l1: str,
        l2: str,
        l3: str,
        l4: str,
    ) -> MemoryContext:
        task_type = self.classify_task(user_text)
        items = [
            *self._parse_layer_items("L1", l1),
            *self._parse_layer_items("L2", l2),
            *self._parse_layer_items("L3", l3),
            *self._parse_layer_items("L4", l4),
        ]
        scored = score_items(query=user_text, task_type=task_type, items=items)
        ranked = rank_items(items=scored, task_type=task_type)
        deduped = dedupe_items(ranked)
        selected = self._assemble_by_budget(deduped, self.budget_for_task(task_type))

        return MemoryContext(
            task_type=task_type,
            l0=self._trim(l0, self.budgets.l0),
            l1=selected.get("L1", "(empty)"),
            l2=selected.get("L2", "(empty)"),
            l3=selected.get("L3", "(empty)"),
            l4=selected.get("L4", "(empty)"),
        )

    def dedupe_items(self, items: list[MemoryItem]) -> list[MemoryItem]:
        return dedupe_items(items)

    def _assemble_by_budget(self, items: list[MemoryItem], budgets: dict[str, int]) -> dict[str, str]:
        buckets: dict[str, list[str]] = {"L1": [], "L2": [], "L3": [], "L4": []}
        remaining = dict(budgets)
        for item in items:
            layer = item.layer
            if layer not in remaining or remaining[layer] <= 0:
                continue
            text = self._trim(item.text, remaining[layer])
            if not text or text == "(empty)":
                continue
            buckets[layer].append(text)
            remaining[layer] -= len(text)
        return {layer: ("\n".join(rows) if rows else "(empty)") for layer, rows in buckets.items()}

    def _parse_layer_items(self, layer: str, text: str) -> list[MemoryItem]:
        if not text or text == "(empty)":
            return []
        items: list[MemoryItem] = []
        for idx, line in enumerate(text.splitlines()):
            normalized = line.strip()
            if not normalized:
                continue
            cleaned = re.sub(r"^\[(?:L[1-4]|l[1-4])\]\s*", "", normalized)
            lowered = cleaned.lower()
            # Prefer earlier rows slightly when upstream has coarse ordering only.
            recency = max(0.0, 0.5 - idx * 0.05)
            items.append(
                MemoryItem(
                    layer=layer,
                    text=cleaned,
                    evidence="tool:verified" if "tool:" in lowered else "",
                    source="query_memory",
                    verified=("verified" in lowered or lowered.startswith("v:")),
                    recency=recency,
                )
            )
        return items

    @staticmethod
    def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)

    @staticmethod
    def _trim(text: str, limit: int) -> str:
        if not text:
            return "(empty)"
        if text == "(empty)" or len(text) <= limit:
            return text
        if limit <= 3:
            return text[: max(limit, 0)]
        return f"{text[: limit - 3]}..."
