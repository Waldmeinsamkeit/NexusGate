import tempfile
import unittest
from pathlib import Path

from nexusgate.memory.manager import MemoryManager


class MemoryManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name) / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.source_root = Path(self.tmpdir.name) / "source"
        (self.source_root / "assets").mkdir(parents=True, exist_ok=True)
        (self.source_root / "memory").mkdir(parents=True, exist_ok=True)

        (self.source_root / "memory" / "memory_management_sop.md").write_text(
            "No Execution, No Memory.\n禁止存储易变状态。\n",
            encoding="utf-8",
        )
        (self.source_root / "assets" / "insight_fixed_structure.txt").write_text(
            "[Global Memory Insight]\n",
            encoding="utf-8",
        )
        (self.source_root / "assets" / "global_mem_insight_template.txt").write_text(
            "L1 template\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_validate_memory_write_requires_evidence(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        self.assertFalse(manager.validate_memory_write("stable fact", ""))
        self.assertFalse(manager.validate_memory_write("session id=123", "tool:ok"))
        self.assertTrue(manager.validate_memory_write("stable fact", "tool:ok"))

    def test_build_memory_header_contains_sections(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        manager.upsert_memory(
            layer="L2",
            session_id="s1",
            text="数据库端口为 5432",
            evidence="shell: cat config",
        )
        header = manager.build_memory_header(session_id="s1", query="数据库端口")
        self.assertIn("<memory_index>", header)
        self.assertIn("<relevant_memory>", header)
        self.assertIn("数据库端口", header)

    def test_enrich_messages_injects_system_context(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        messages = [{"role": "user", "content": "你好"}]
        enriched = manager.enrich_messages(messages=messages, metadata={"session_id": "s2"})
        self.assertEqual(enriched[0]["role"], "system")
        self.assertIn("<nexus_context>", enriched[0]["content"])

    def test_start_memory_update_archives_l4(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        messages = [
            {"role": "user", "content": "请修复启动脚本"},
            {"role": "assistant", "content": "已修复"},
        ]
        manager.start_memory_update(
            session_id="s3",
            messages=messages,
            final_result="任务成功，脚本可启动",
        )
        text = manager.query_memory("s3", "启动脚本", layers=["L4"])
        self.assertIn("启动脚本", text)


if __name__ == "__main__":
    unittest.main()
