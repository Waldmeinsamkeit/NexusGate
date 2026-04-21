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
            "No Execution, No Memory.\n",
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
        (self.source_root / "memory" / "global_mem.txt").write_text(
            "## [FACTS]\n",
            encoding="utf-8",
        )
        (self.source_root / "memory" / "session_memory_recall.md").write_text(
            "---\n"
            "key: session_memory_recall\n"
            "one_line_summary: Recover prior session state.\n"
            "tags:\n"
            "  - session\n"
            "  - memory\n"
            "  - recall\n"
            "---\n\n"
            "## When to use\n"
            "- Continue from prior round\n\n"
            "## Core rules\n"
            "1. Only trust tool-verified artifacts.\n",
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
            text="database port is 5432",
            evidence="shell: cat config",
        )
        manager.upsert_memory(
            layer="L3",
            session_id="s1",
            text="skill: inspect startup config and service ports",
            evidence="tool:ok",
        )
        manager.upsert_memory(
            layer="L4",
            session_id="s1",
            text="previous session discussed startup script rollback",
            evidence="tool:archive_success",
        )
        header = manager.build_memory_header(session_id="s1", query="database port")
        self.assertIn("<memory_index>", header)
        self.assertIn("<relevant_skills>", header)
        self.assertIn("<session_recall_hints>", header)
        self.assertIn("<relevant_memory>", header)
        self.assertIn("database port is 5432", header)
        self.assertIn("skill: inspect startup config and service ports", header)
        self.assertIn("previous session discussed startup script rollback", header)

    def test_enrich_messages_injects_system_context(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        messages = [{"role": "user", "content": "hello"}]
        enriched = manager.enrich_messages(messages=messages, metadata={"session_id": "s2"})
        self.assertEqual(enriched[0]["role"], "system")
        self.assertIn("<nexus_context>", enriched[0]["content"])

    def test_bv1_indexes_session_recall_skill_on_startup(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        indexed = manager.query_memory(
            manager.SKILL_INDEX_SESSION_ID,
            "session_memory_recall",
            layers=["L3"],
        )
        self.assertIn("skill: session_memory_recall", indexed)
        self.assertIn("summary: Recover prior session state.", indexed)
        self.assertIn("tags: session, memory, recall", indexed)

    def test_bv1_trigger_query_retrieves_indexed_skill(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        header = manager.build_memory_header(session_id="s2", query="请回忆上次 session 的处理过程")
        self.assertIn("skill: session_memory_recall", header)
        self.assertIn("Continue from prior round", header)

    def test_bv1_normal_query_does_not_force_skill(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        header = manager.build_memory_header(session_id="s2", query="explain db connection pool")
        self.assertNotIn("skill: session_memory_recall", header)

    def test_bv1_missing_skill_file_degrades_safely(self) -> None:
        missing_root = Path(self.tmpdir.name) / "source-no-skill"
        (missing_root / "assets").mkdir(parents=True, exist_ok=True)
        (missing_root / "memory").mkdir(parents=True, exist_ok=True)
        (missing_root / "memory" / "memory_management_sop.md").write_text(
            "No Execution, No Memory.\n",
            encoding="utf-8",
        )
        (missing_root / "memory" / "global_mem.txt").write_text(
            "## [FACTS]\n",
            encoding="utf-8",
        )
        (missing_root / "assets" / "insight_fixed_structure.txt").write_text(
            "[Global Memory Insight]\n",
            encoding="utf-8",
        )
        (missing_root / "assets" / "global_mem_insight_template.txt").write_text(
            "L1 template\n",
            encoding="utf-8",
        )

        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace / "no-skill"),
            source_root=str(missing_root),
            use_chroma=False,
        )
        header = manager.build_memory_header(session_id="s2", query="回忆上一轮会话")
        self.assertIn("<relevant_skills>", header)
        self.assertNotIn("skill: session_memory_recall", header)

    def test_start_memory_update_archives_l4(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        messages = [
            {"role": "user", "content": "please fix startup script"},
            {"role": "assistant", "content": "fixed"},
        ]
        manager.start_memory_update(
            session_id="s3",
            messages=messages,
            final_result="done and startup script works",
        )
        text = manager.query_memory("s3", "startup script", layers=["L4"])
        self.assertIn("startup script", text)
        l2_text = manager.query_memory("s3", "done and startup script works", layers=["L2"])
        self.assertIn("done and startup script works", l2_text)

    def test_l4_archive_persisted_and_reloaded_when_no_chroma(self) -> None:
        manager = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        messages = [
            {"role": "user", "content": "create file codex_write_test.txt"},
            {"role": "assistant", "content": "file created"},
        ]
        manager.archive_session(session_id="s4", messages=messages)

        archive_file = self.workspace / "l4" / "archive.jsonl"
        self.assertTrue(archive_file.exists())
        self.assertIn("codex_write_test.txt", archive_file.read_text(encoding="utf-8"))

        reloaded = MemoryManager(
            enabled=True,
            store_path=str(self.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        text = reloaded.query_memory("s4", "codex_write_test.txt", layers=["L4"])
        self.assertIn("codex_write_test.txt", text)


if __name__ == "__main__":
    unittest.main()
