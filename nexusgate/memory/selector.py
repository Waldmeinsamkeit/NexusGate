from __future__ import annotations

from nexusgate.memory.models import LayerBudgets, MemoryContext, ScoredMemory
from nexusgate.memory.scoring import dedupe_items
from nexusgate.memory.policies import (
    CODING_HINTS,
    DEBUG_HINTS,
    PLANNING_HINTS,
    RECALL_HINTS,
    budget_for_task as policy_budget_for_task,
)


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
        items_by_layer: dict[str, list[ScoredMemory]] | None = None,
        l1: str = "(empty)",
        l2: str = "(empty)",
        l3: str = "(empty)",
        l4: str = "(empty)",
    ) -> MemoryContext:
        task_type = self.classify_task(user_text)
        budget = self.budget_for_task(task_type)
        source_items = items_by_layer or {
            "L1": self._parse_layer_items("L1", l1),
            "L2": self._parse_layer_items("L2", l2),
            "L3": self._parse_layer_items("L3", l3),
            "L4": self._parse_layer_items("L4", l4),
        }
        selected_items = self.select_items_by_layer(source_items, budget)
        return MemoryContext(
            task_type=task_type,
            l0=self._trim(l0, self.budgets.l0),
            l1=self.render_items(selected_items.get("L1", []), budget["L1"]),
            l2=self.render_items(selected_items.get("L2", []), budget["L2"]),
            l3=self.render_items(selected_items.get("L3", []), budget["L3"]),
            l4=self.render_items(selected_items.get("L4", []), budget["L4"]),
        )

    def select_items_by_layer(
        self,
        items_by_layer: dict[str, list[ScoredMemory]],
        budget: dict[str, int],
    ) -> dict[str, list[ScoredMemory]]:
        return {
            "L1": self.select_layer_items(items_by_layer.get("L1", []), budget.get("L1", 0)),
            "L2": self.select_layer_items(items_by_layer.get("L2", []), budget.get("L2", 0)),
            "L3": self.select_layer_items(items_by_layer.get("L3", []), budget.get("L3", 0)),
            "L4": self.select_layer_items(items_by_layer.get("L4", []), budget.get("L4", 0)),
        }

    @staticmethod
    def select_layer_items(items: list[ScoredMemory], budget: int) -> list[ScoredMemory]:
        selected: list[ScoredMemory] = []
        remaining = max(budget, 0)
        for item in items:
            text = item.text.strip()
            if remaining <= 0:
                break
            if not text:
                continue
            if len(text) > remaining:
                continue
            selected.append(item)
            remaining -= len(text)
        return selected

    @staticmethod
    def render_items(items: list[ScoredMemory], budget: int) -> str:
        if not items or budget <= 0:
            return "(empty)"
        rows = [item.text.strip() for item in items if item.text.strip()]
        return "\n".join(rows) if rows else "(empty)"

    def dedupe_items(self, items: list[ScoredMemory]) -> list[ScoredMemory]:
        return dedupe_items(items)

    @staticmethod
    def _parse_layer_items(layer: str, text: str) -> list[ScoredMemory]:
        if not text or text == "(empty)":
            return []
        items: list[ScoredMemory] = []
        for line in text.splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            if normalized.startswith(f"[{layer}]"):
                normalized = normalized[len(layer) + 2 :].strip()
            items.append(ScoredMemory(layer=layer, text=normalized))
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


MemoryItem = ScoredMemory
