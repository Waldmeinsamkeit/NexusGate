from __future__ import annotations

from nexusgate.memory.models import LayerBudgets


DEBUG_HINTS = ("traceback", "error", "exception", "bug", "报错", "异常")
CODING_HINTS = ("代码", "patch", "refactor", "实现", "修改", "test", "fix")
PLANNING_HINTS = ("计划", "规划", "方案", "步骤", "roadmap", "plan")
RECALL_HINTS = ("回忆", "之前", "上次", "历史", "session", "l4", "context", "recall")

TASK_LAYER_WEIGHTS = {
    "coding": {"L1": 0.8, "L2": 1.6, "L3": 2.2, "L4": 0.9},
    "debug": {"L1": 0.8, "L2": 2.1, "L3": 1.8, "L4": 1.1},
    "planning": {"L1": 1.8, "L2": 1.0, "L3": 2.0, "L4": 0.8},
    "retrieval-only": {"L1": 0.8, "L2": 1.8, "L3": 1.1, "L4": 2.2},
    "chat": {"L1": 1.2, "L2": 1.1, "L3": 0.9, "L4": 0.7},
}

TASK_LAYER_BUDGET_FACTORS = {
    "coding": {"L1": 0.45, "L2": 0.9, "L3": 1.0, "L4": 0.75},
    "debug": {"L1": 0.45, "L2": 1.0, "L3": 0.9, "L4": 0.55},
    "planning": {"L1": 0.9, "L2": 0.55, "L3": 1.0, "L4": 0.35},
    "retrieval-only": {"L1": 0.4, "L2": 0.9, "L3": 0.3, "L4": 1.0},
    "chat": {"L1": 0.5, "L2": 0.5, "L3": 0.4, "L4": 0.3},
}

SUCCESS_POSITIVE_HINTS = (
    "success",
    "completed",
    "done",
    "passed",
    "test passed",
    "tests passed",
    "updated file",
    "exit code 0",
)
SUCCESS_NEGATIVE_HINTS = (
    "maybe",
    "likely",
    "uncertain",
    "not sure",
    "failed",
    "error",
    "exception",
    "cannot",
)

EVIDENCE_PRIORITY_HINTS = ("tool:", "shell", "file", "archive", "success", "pass", "ok")


def budget_for_task(task_type: str, base: LayerBudgets) -> dict[str, int]:
    factors = TASK_LAYER_BUDGET_FACTORS.get(task_type, TASK_LAYER_BUDGET_FACTORS["chat"])
    raw = {
        "L1": int(base.l1 * factors["L1"]),
        "L2": int(base.l2 * factors["L2"]),
        "L3": int(base.l3 * factors["L3"]),
        "L4": int(base.l4 * factors["L4"]),
    }
    return {layer: max(value, 0) for layer, value in raw.items()}
