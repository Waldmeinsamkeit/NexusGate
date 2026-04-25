from __future__ import annotations

import re

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

    def budget_for_task(self, task_type: str, max_total_chars: int | None = None) -> dict[str, int]:
        base = policy_budget_for_task(task_type, self.budgets)
        if not max_total_chars or max_total_chars <= 0:
            return base
        base_total = sum(int(v) for v in base.values())
        if base_total <= 0:
            return base
        cap = max(int(max_total_chars), 1)
        if cap >= base_total:
            return base
        scaled: dict[str, int] = {}
        for key, value in base.items():
            proportion = float(int(value)) / float(base_total)
            scaled[key] = max(int(cap * proportion), 1) if int(value) > 0 else 0
        # Correct rounding drift.
        drift = cap - sum(scaled.values())
        if drift != 0:
            for key in ("L2", "L3", "L1", "L4"):
                if key in scaled and scaled[key] > 0:
                    scaled[key] = max(scaled[key] + drift, 1)
                    break
        return scaled

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
        # L2 facts matching L1 pointers get unlimited budget (handled in build_memory_pack)
        selected = {
            "L1": self.select_layer_items(items_by_layer.get("L1", []), budget.get("L1", 0)),
            "L2": self.select_layer_items(items_by_layer.get("L2", []), budget.get("L2", 0)),
            "L3": self.select_layer_items(items_by_layer.get("L3", []), budget.get("L3", 0)),
            "L4": self.select_layer_items(items_by_layer.get("L4", []), budget.get("L4", 0)),
        }
        return {
            layer: self.resolve_conflicts(rows)
            for layer, rows in selected.items()
        }

    @staticmethod
    def select_layer_items(items: list[ScoredMemory], budget: int) -> list[ScoredMemory]:
        selected: list[ScoredMemory] = []
        unlimited = budget <= 0  # budget=0 means unlimited (no trimming)
        remaining = max(budget, 0) if not unlimited else 0
        for item in items:
            text = item.text.strip()
            if not unlimited and remaining <= 0:
                break
            if not text:
                continue
            if not unlimited and len(text) > remaining:
                # Truncate rather than skip — a partial fact is better than none
                text = text[:remaining]
            selected.append(
                ScoredMemory(
                    layer=item.layer,
                    text=text,
                    memory_id=item.memory_id,
                    evidence=item.evidence,
                    source=item.source,
                    verified=item.verified,
                    confidence=item.confidence,
                    score=item.score,
                    recency=item.recency,
                )
            )
            if not unlimited:
                remaining -= len(text)
        return selected

    @staticmethod
    def render_items(items: list[ScoredMemory], budget: int) -> str:
        if not items:
            return "(empty)"
        rows: list[str] = []
        for item in items:
            text = item.text.strip()
            if not text:
                continue
            if (not item.verified) or float(item.confidence or 0.0) < 0.6:
                text = f"[unverified] {text}"
            rows.append(text)
        return "\n".join(rows) if rows else "(empty)"

    def resolve_conflicts(self, items: list[ScoredMemory]) -> list[ScoredMemory]:
        if len(items) <= 1:
            return items
        latest_by_subject: dict[str, ScoredMemory] = {}
        passthrough: list[ScoredMemory] = []
        for item in items:
            subject_value = self._subject_value(item.text)
            if subject_value is None:
                passthrough.append(item)
                continue
            subject, _ = subject_value
            existing = latest_by_subject.get(subject)
            if existing is None:
                latest_by_subject[subject] = item
                continue
            latest_by_subject[subject] = self._pick_better(existing, item)
        resolved = [*latest_by_subject.values(), *passthrough]
        return sorted(resolved, key=lambda row: (row.score, row.verified, row.confidence, row.recency), reverse=True)

    @staticmethod
    def _pick_better(a: ScoredMemory, b: ScoredMemory) -> ScoredMemory:
        rank_a = (a.verified, float(a.confidence or 0.0), a.recency, a.score)
        rank_b = (b.verified, float(b.confidence or 0.0), b.recency, b.score)
        return a if rank_a >= rank_b else b

    @staticmethod
    def _subject_value(text: str) -> tuple[str, str] | None:
        lowered = (text or "").strip().lower()
        if not lowered:
            return None
        match = re.search(
            r"([a-z_][a-z0-9_\-./]{1,40}|[\u4e00-\u9fff]{2,8})\s*(?:[:=]|是|为)\s*([a-z0-9_./:\-]{1,80}|\d+)",
            lowered,
        )
        if not match:
            return None
        subject = (match.group(1) or "").strip()
        value = (match.group(2) or "").strip()
        if not subject or not value:
            return None
        return subject, value

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
