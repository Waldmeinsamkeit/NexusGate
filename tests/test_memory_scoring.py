import unittest

from nexusgate.memory.models import MemoryItem
from nexusgate.memory.scoring import dedupe_items, dedupe_key, score_items


class MemoryScoringTests(unittest.TestCase):
    def test_chinese_query_overlap_increases_score(self) -> None:
        items = [
            MemoryItem(layer="L2", text="稳定事实: 启动脚本路径 startup.sh"),
            MemoryItem(layer="L2", text="stable_fact: unrelated config"),
        ]
        scored = score_items(query="请回忆启动脚本", task_type="retrieval-only", items=items)
        self.assertGreater(scored[0].score, scored[1].score)

    def test_verified_item_gets_priority(self) -> None:
        items = [
            MemoryItem(layer="L2", text="stable_fact: config/startup.toml", verified=False),
            MemoryItem(layer="L2", text="stable_fact: config/startup.toml", verified=True),
        ]
        deduped = dedupe_items(items)
        self.assertEqual(len(deduped), 1)
        self.assertTrue(deduped[0].verified)

    def test_dedupe_key_normalizes_punctuation(self) -> None:
        key1 = dedupe_key("Stable_Fact: config/startup.toml!!!")
        key2 = dedupe_key("stable fact config/startup.toml")
        self.assertEqual(key1, key2)


if __name__ == "__main__":
    unittest.main()
