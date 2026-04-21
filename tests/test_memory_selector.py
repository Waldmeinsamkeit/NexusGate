import unittest

from nexusgate.memory.selector import LayerBudgets, MemoryItem, MemorySelector


class MemorySelectorTests(unittest.TestCase):
    def test_classify_task(self) -> None:
        selector = MemorySelector()
        self.assertEqual(selector.classify_task("traceback error"), "debug")
        self.assertEqual(selector.classify_task("please fix code and add test"), "coding")
        self.assertEqual(selector.classify_task("please plan implementation"), "planning")
        self.assertEqual(selector.classify_task("recall previous session"), "retrieval-only")
        self.assertEqual(selector.classify_task("hello"), "chat")

    def test_trim_by_budget(self) -> None:
        selector = MemorySelector(budgets=LayerBudgets(l0=10, l1=10, l2=10, l3=10, l4=10))
        ctx = selector.select(
            user_text="hello",
            l0="1234567890123",
            l1="line1\nline2",
            l2="line1\nline2",
            l3="line1\nline2",
            l4="line1\nline2",
        )
        self.assertEqual(ctx.l0, "1234567...")
        self.assertLessEqual(len(ctx.l4), 10)

    def test_budget_for_task_is_dynamic(self) -> None:
        selector = MemorySelector()
        coding_budget = selector.budget_for_task("coding")
        retrieval_budget = selector.budget_for_task("retrieval-only")

        self.assertGreater(coding_budget["L3"], coding_budget["L4"])
        self.assertGreater(retrieval_budget["L4"], retrieval_budget["L3"])

    def test_dedupe_prefers_verified_items(self) -> None:
        selector = MemorySelector()
        items = [
            MemoryItem(layer="L2", text="Database port is 5432", verified=False),
            MemoryItem(layer="L4", text="Database port is 5432", verified=True),
        ]
        deduped = selector.dedupe_items(items)

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].layer, "L4")
        self.assertTrue(deduped[0].verified)

    def test_coding_prefers_l3_and_keeps_l4_for_recall(self) -> None:
        selector = MemorySelector(budgets=LayerBudgets(l0=80, l1=80, l2=80, l3=80, l4=80))
        ctx = selector.select(
            user_text="fix startup script and recall previous session",
            l0="l0",
            l1="index pointer",
            l2="[L2] startup script depends on config key",
            l3="[L3] task_takeaway: run startup fix before tests",
            l4="[L4] startup script failed in previous session",
        )
        self.assertEqual(ctx.task_type, "coding")
        self.assertIn("task_takeaway", ctx.l3)
        self.assertIn("previous session", ctx.l4)


if __name__ == "__main__":
    unittest.main()
