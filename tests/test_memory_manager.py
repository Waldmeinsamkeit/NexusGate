import json
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
        manifest = [
            {
                "name": "session_memory_recall",
                "path": "session_memory_recall.md",
                "triggers": ["recall", "session", "history", "l4"],
                "task_types": ["retrieval-only", "debug", "planning", "chat"],
                "injection_mode": "summary",
            }
        ]
        (self.source_root / "memory" / "skill_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _new_manager(self, suffix: str = "") -> MemoryManager:
        store = self.workspace / (f"store{suffix}" if suffix else "store")
        return MemoryManager(
            enabled=True,
            store_path=str(store),
            source_root=str(self.source_root),
            use_chroma=False,
        )

    def test_validate_memory_write_requires_evidence(self) -> None:
        manager = self._new_manager("-validate")
        self.assertFalse(manager.validate_memory_write("stable fact", ""))
        self.assertFalse(manager.validate_memory_write("session id=123", "tool:ok"))
        self.assertTrue(manager.validate_memory_write("stable fact", "tool:ok"))

    def test_build_memory_header_contains_sections(self) -> None:
        manager = self._new_manager("-header")
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

    def test_build_memory_header_keeps_l1_outside_relevant_memory(self) -> None:
        manager = self._new_manager("-header-no-mix")
        manager.upsert_memory(
            layer="L1",
            session_id="s1",
            text="memory_write_rules -> L2",
            evidence="tool:ok",
        )
        manager.upsert_memory(
            layer="L2",
            session_id="s1",
            text="stable_fact: config/startup.toml",
            evidence="tool:ok",
        )
        header = manager.build_memory_header(session_id="s1", query="startup")
        self.assertIn("memory_write_rules -> L2", header)

        relevant_block = header.split("<relevant_memory>\n", 1)[1].split("\n</relevant_memory>", 1)[0]
        self.assertIn("config/startup.toml", relevant_block)
        self.assertNotIn("memory_write_rules -> L2", relevant_block)

    def test_manifest_trigger_query_retrieves_session_skill(self) -> None:
        manager = self._new_manager("-skill")
        header = manager.build_memory_header(session_id="s2", query="please recall previous session")
        self.assertIn("skill: session_memory_recall", header)

    def test_l4_summary_only_not_l2_summary(self) -> None:
        manager = self._new_manager("-l4only")
        messages = [
            {"role": "user", "content": "help me fix startup"},
            {"role": "assistant", "content": "working"},
        ]
        manager.start_memory_update(
            session_id="s3",
            messages=messages,
            final_result="done",
        )

        l4_text = manager.query_memory("s3", "startup", layers=["L4"])
        l2_text = manager.query_memory("s3", "Conversation summary", layers=["L2"])
        self.assertIn("[USER]", l4_text)
        self.assertNotIn("Conversation summary", l2_text)

    def test_unverified_candidates_do_not_enter_high_layers(self) -> None:
        manager = self._new_manager("-gate")
        messages = [
            {"role": "user", "content": "sync memory"},
            {"role": "assistant", "content": "attempting"},
        ]
        manager.start_memory_update(
            session_id="s4",
            messages=messages,
            final_result="likely done maybe",
        )

        l1_text = manager.query_memory("s4", "memory_write_rules", layers=["L1"])
        l2_text = manager.query_memory("s4", "stable fact", layers=["L2"])
        l3_text = manager.query_memory("s4", "task_takeaway", layers=["L3"])
        self.assertEqual(l1_text, "(empty)")
        self.assertEqual(l2_text, "(empty)")
        self.assertEqual(l3_text, "(empty)")

    def test_explicit_success_generates_l1_l2_l3(self) -> None:
        manager = self._new_manager("-success")
        messages = [
            {"role": "user", "content": "fix startup script and run tests"},
            {"role": "assistant", "content": "updated file config/startup.toml and test passed"},
        ]
        manager.start_memory_update(
            session_id="s5",
            messages=messages,
            final_result="success: updated file config/startup.toml, tests passed",
        )

        l1_text = manager.query_memory("s5", "memory_write_rules", layers=["L1"])
        l2_text = manager.query_memory("s5", "config/startup.toml", layers=["L2"])
        l3_text = manager.query_memory("s5", "task_takeaway", layers=["L3"])
        self.assertIn("memory_write_rules -> L2", l1_text)
        self.assertIn("config/startup.toml", l2_text)
        self.assertIn("task_takeaway", l3_text)

    def test_l4_archive_persisted_and_reloaded_when_no_chroma(self) -> None:
        manager = self._new_manager("-archive")
        messages = [
            {"role": "user", "content": "create file codex_write_test.txt"},
            {"role": "assistant", "content": "file created"},
        ]
        manager.archive_session(session_id="s6", messages=messages)

        archive_file = manager.l4_archive_path
        self.assertTrue(archive_file.exists())
        self.assertIn("codex_write_test.txt", archive_file.read_text(encoding="utf-8"))

        reloaded = MemoryManager(
            enabled=True,
            store_path=str(manager.workspace),
            source_root=str(self.source_root),
            use_chroma=False,
        )
        text = reloaded.query_memory("s6", "codex_write_test.txt", layers=["L4"])
        self.assertIn("codex_write_test.txt", text)


if __name__ == "__main__":
    unittest.main()
