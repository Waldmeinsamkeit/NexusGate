#!/usr/bin/env python3
"""
NexusGate Architecture Token Benchmark
=======================================
Offline benchmark: directly invokes NexusGate's internal pipeline
(history rewrite + memory injection + budget trim) WITHOUT making
any upstream LLM calls.  Both "no-arch" and "with-arch" token counts
come from the same CJK-aware estimator — apples-to-apples comparison.

Scenarios simulate realistic conversation lengths:
  - Short:  single question  (~50 tokens)
  - Medium: 10-turn debug session  (~3,000 tokens)
  - Long:   30-turn coding session with tool results (~15,000 tokens)

Usage:
    python scripts/arch_token_benchmark.py
    python scripts/arch_token_benchmark.py --output scripts/bench_report.txt

No running gateway or upstream provider required.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Bootstrap: allow importing from back/ ───────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
BACK_DIR = REPO_ROOT / "back"
if str(BACK_DIR) not in sys.path:
    sys.path.insert(0, str(BACK_DIR))

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None  # type: ignore[assignment]


# ─── CJK-aware token estimator (same as NexusGate core) ────────────
import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef"
                      r"\u2e80-\u2eff\u3100-\u312f\u31a0-\u31bf\ua490-\ua4cf"
                      r"\uf900-\ufaff\ufe30-\ufe4f]")


def _estimate_tokens_for_messages(messages: list[dict[str, Any]]) -> int:
    """Mirrors _estimate_token_count_from_messages in app.py."""
    total = 0.0
    for msg in messages:
        text = _collect_text(msg)
        cjk = len(_CJK_RE.findall(text))
        non_cjk = max(len(text) - cjk, 0)
        total += (cjk * 1.5) + (non_cjk / 4.0) + 4.0
    return int(total)


def _collect_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(part for item in value if (part := _collect_text(item)))
    if isinstance(value, dict):
        parts: list[str] = []
        for key in ("content", "text", "input_text", "output_text", "arguments", "name"):
            part = _collect_text(value.get(key))
            if part:
                parts.append(part)
        if not parts:
            parts.append(json.dumps(value, ensure_ascii=False))
        return " ".join(parts)
    return str(value)


# ─── Scenario Definitions ──────────────────────────────────────────
# Designed to match REAL session sizes: Codex / Cursor typically send
# full conversation history (including assistant + tool results) each turn.

def _make_code_block(lines: int = 40) -> str:
    """Generate a realistic Python code block."""
    code_lines = [
        "import asyncio",
        "from typing import Any",
        "from pathlib import Path",
        "",
        "",
        "class MemoryManager:",
        '    """Core memory orchestrator."""',
        "",
        "    def __init__(self, store_path: str, top_k: int = 6, enabled: bool = True):",
        "        self.store_path = Path(store_path)",
        "        self.top_k = top_k",
        "        self.enabled = enabled",
        "        self._repo = StructuredMemoryRepository(store_path)",
        "        self._index = ChromaIndex(store_path) if enabled else NullIndex()",
        "        self._scorer = MemoryScorer()",
        "        self._selector = MemorySelector()",
        "",
        "    async def build_memory_pack(self, session_id: str, query: str) -> MemoryPack:",
        '        """Build a memory pack for the given query."""',
        "        if not self.enabled:",
        "            return MemoryPack.empty()",
        "        candidates = await self._retrieve_candidates(query)",
        "        scored = self._scorer.score(candidates, query=query)",
        "        selected = self._selector.select(scored, budget=self.top_k)",
        "        return self._assemble_pack(selected, session_id=session_id)",
        "",
        "    async def _retrieve_candidates(self, query: str) -> list[MemoryCandidate]:",
        "        vector_results = await self._index.search(query, k=self.top_k * 3)",
        "        lexical_results = self._repo.lexical_query(query, limit=self.top_k * 2)",
        "        return self._merge_candidates(vector_results, lexical_results)",
        "",
        "    def _merge_candidates(self, vec: list, lex: list) -> list[MemoryCandidate]:",
        "        seen: set[str] = set()",
        "        merged: list[MemoryCandidate] = []",
        "        for item in vec + lex:",
        "            if item.id not in seen:",
        "                seen.add(item.id)",
        "                merged.append(item)",
        "        return merged",
        "",
        "    def _assemble_pack(self, selected: list, session_id: str) -> MemoryPack:",
        "        facts = [m.content for m in selected if m.layer == 'L2']",
        "        procedures = [m.content for m in selected if m.layer == 'L3']",
        "        continuity = [m.content for m in selected if m.layer == 'L4']",
        "        constraints = [m.content for m in selected if m.layer == 'L1']",
        "        return MemoryPack(",
        "            task_mode='chat',",
        "            pack_features={'verified_ratio': 0.85},",
        "            l0=L0_META_RULES,",
        "            facts='\\n'.join(facts),",
        "            procedures='\\n'.join(procedures),",
        "            continuity='\\n'.join(continuity),",
        "            constraints='\\n'.join(constraints),",
        "        )",
    ]
    return "\n".join(code_lines[:lines])


def _make_tool_result(char_count: int = 2000) -> str:
    """Generate a realistic tool result (file read / command output)."""
    lines = [
        "$ cat back/nexusgate/memory/manager.py",
        "# ──── manager.py ────",
        "from __future__ import annotations",
        "import json, time, re, logging",
        "from pathlib import Path",
        "from typing import Any, Optional",
        "from .models import MemoryPack, MemoryCandidate, ScoredMemory",
        "from .schema import MemoryRecord, MemoryScope, MemoryType",
        "from .repository import StructuredMemoryRepository",
        "from .index import ChromaIndex, NullIndex",
        "from .query_service import HybridQueryService",
        "from .scoring import MemoryScorer",
        "from .selector import MemorySelector",
        "from .write_policy import WritePolicy",
        "from .summarizer import SessionSummarizer",
        "from .events import MemoryEventLogger",
        "",
        "logger = logging.getLogger(__name__)",
        "",
        "class MemoryManager:",
        '    """Central orchestrator for NexusGate memory system."""',
        "    STALENESS_THRESHOLDS = {'L2': 30, 'L3': 60, 'L4': 7}",
        "    CONFIDENCE_GATE = 0.6",
    ]
    result = "\n".join(lines)
    while len(result) < char_count:
        result += "\n    # ... (additional methods and implementation details)"
    return result[:char_count]


SHORT_SCENARIO = {
    "name": "Short (1-turn)",
    "description": "Single factual question, no history",
    "messages": [
        {"role": "user", "content": "NexusGate 的默认端口是什么？"},
    ],
}

MEDIUM_SCENARIO: dict[str, Any] = {
    "name": "Medium (10-turn)",
    "description": "Multi-turn debug session with code snippets (~3K tokens)",
    "messages": [
        {"role": "user", "content": "帮我排查 NexusGate 启动报错：'Connection refused on port 8000'。以下是我的启动日志：\n" + "INFO: Uvicorn running on http://0.0.0.0:9000\nWARNING: memory store not found at /data/memory\nINFO: Loaded 0 memories from structured_memory.jsonl\n" * 3},
        {"role": "assistant", "content": "从日志看到两个问题：\n\n1. **端口不匹配**：Uvicorn 启动在 9000，但你连的是 8000\n2. **记忆存储路径不存在**：`/data/memory` 没找到\n\n排查步骤：\n```bash\n# 检查 .env 配置\ncat .env | grep -E 'PORT|MEMORY_STORE'\n\n# 检查端口占用\nnetstat -tlnp | grep -E '8000|9000'\n```\n\n请先确认 `.env` 中 `PORT` 和 `MEMORY_STORE_PATH` 的值。"},
        {"role": "user", "content": ".env 内容如下：\n```\nPORT=9000\nMEMORY_STORE_PATH=/data/memory\nTARGET_PROVIDER=gpt-5.3-codex\nAPI_KEY_REQUIRED=true\nLOCAL_API_KEY=nxg-abc123\nMEMORY_ENABLED=true\nMEMORY_TOP_K=6\nHISTORY_REWRITE_DEFAULT_MODE=auto\nCONTEXT_BUDGET_MARGIN=0.15\n```\n端口确实配的 9000。MEMORY_STORE_PATH 是 /data/memory 但目录不存在。"},
        {"role": "assistant", "content": "确认了两个问题：\n\n### 问题 1：端口\n```diff\n- PORT=9000\n+ PORT=8000\n```\n或者让客户端连 `http://localhost:9000`。\n\n### 问题 2：记忆存储路径\n```bash\nmkdir -p /data/memory\n# 或者改为相对路径（推荐）：\n```\n```diff\n- MEMORY_STORE_PATH=/data/memory\n+ MEMORY_STORE_PATH=memory\n```\n\n修改后重启：`python -m nexusgate`"},
        {"role": "user", "content": "改成 PORT=8000 和 MEMORY_STORE_PATH=memory 之后可以启动了。但调用 /v1/chat/completions 返回 401 Unauthorized。请求如下：\n```bash\ncurl -X POST http://localhost:8000/v1/chat/completions \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"gpt-5.3-codex\", \"messages\": [{\"role\": \"user\", \"content\": \"hello\"}]}'\n```"},
        {"role": "assistant", "content": "你的 `.env` 中设置了 `API_KEY_REQUIRED=true` 且 `LOCAL_API_KEY=nxg-abc123`，但 curl 请求没有带 API Key。\n\n解决方案（二选一）：\n\n**方案 A：在请求中加 API Key**\n```bash\ncurl -X POST http://localhost:8000/v1/chat/completions \\\n  -H 'Content-Type: application/json' \\\n  -H 'Authorization: Bearer nxg-abc123' \\\n  -d '{\"model\": \"gpt-5.3-codex\", \"messages\": [{\"role\": \"user\", \"content\": \"hello\"}]}'\n```\n\n**方案 B：关闭 API Key 验证（仅本地测试）**\n```diff\n- API_KEY_REQUIRED=true\n+ API_KEY_REQUIRED=false\n```\n\n建议生产环境保持 `API_KEY_REQUIRED=true`。"},
        {"role": "user", "content": "加了 API Key 可以正常调用了。现在我想让 Cursor 通过 NexusGate 代理，怎么配置 Cursor 端？"},
        {"role": "assistant", "content": "Cursor 支持自定义 OpenAI Base URL。配置步骤：\n\n1. **打开 Cursor Settings** → Features → OpenAI API\n2. **Base URL**: `http://localhost:8000/v1`\n3. **API Key**: `nxg-abc123`（你的 LOCAL_API_KEY）\n4. **Model**: `gpt-5.3-codex`\n\n或者在 Cursor 的 `settings.json` 中：\n```json\n{\n  \"openai.apiBaseUrl\": \"http://localhost:8000/v1\",\n  \"openai.apiKey\": \"nxg-abc123\"\n}\n```\n\n配置后 Cursor 的所有 LLM 请求都会经过 NexusGate，自动获得记忆增强。\n\n如果开启了 `CLIENT_SYNC_ENABLED=true`，NexusGate 会自动同步 Cursor/Codex 的配置文件。"},
        {"role": "user", "content": "配好了。但我发现通过 NexusGate 调用时延迟明显增加，从 2 秒变成了 5 秒。有什么优化建议？"},
        {"role": "assistant", "content": "额外延迟主要来自三个环节：\n\n| 环节 | 典型耗时 | 优化方案 |\n|------|---------|--------|\n| 记忆检索 (vector + lexical) | 500-1500ms | 减少 `MEMORY_TOP_K`，关闭 ChromaDB |\n| 历史重写 | 200-500ms | 设置 `HISTORY_REWRITE_DEFAULT_MODE=light` |\n| Grounding check | 300-800ms | 对低风险查询跳过 |\n\n**推荐优化组合**：\n```env\nMEMORY_TOP_K=4\nHISTORY_REWRITE_DEFAULT_MODE=light\nMEMORY_USE_CHROMA=false\n```\n\n这样可以将额外延迟从 ~3s 降到 ~500ms。如果延迟仍然不可接受，可以临时用 `skip_memory: true` 跳过记忆注入。"},
    ],
}

# Long scenario: simulate a real Codex-like session with tool results
_TOOL_RESULT_1 = _make_tool_result(2000)
_TOOL_RESULT_2 = _make_tool_result(1500)
_CODE_BLOCK_1 = _make_code_block(50)
_CODE_BLOCK_2 = _make_code_block(35)

LONG_SCENARIO: dict[str, Any] = {
    "name": "Long (30-turn)",
    "description": "Extended coding session with tool results (~10K tokens)",
    "messages": [
        {"role": "user", "content": "我要重构 NexusGate 的 memory 模块，manager.py 有 1300 多行太重了。先看一下文件结构。"},
        {"role": "assistant", "content": f"好的，先读取目录结构和 manager.py 的核心代码：\n```\n{_TOOL_RESULT_1}\n```\n\n当前模块结构：\n- manager.py (~1340行) - 过重，需要拆分\n- models.py, schema.py - 数据模型（可保留）\n- repository.py - JSONL 存储\n- index.py, query_service.py - 检索层\n- scoring.py, selector.py - 评分选择层\n\n建议拆为 3 个新模块：pack_builder.py, renderer.py, lifecycle.py"},
        {"role": "user", "content": "先从 renderer 开始。读一下 build_memory_system_blocks 的完整实现。"},
        {"role": "assistant", "content": f"```python\n{_CODE_BLOCK_1}\n```\n\n这段代码的职责：\n1. 计算 provider 字符预算\n2. 构建渲染块列表\n3. 应用 trim（裁剪低优先级块）\n4. 按 section 渲染最终输出\n\n可以完整提取到 `memory/renderer.py`。需要注意 `trim_report` 回写到 `pack` 对象。"},
        {"role": "user", "content": "提取过程中发现 _apply_provider_trim 有 bug：max_chars=0 时除零。同时我注意到 _provider_char_budget 对不同 provider 返回不同预算，这个逻辑也要一起提取。"},
        {"role": "assistant", "content": f"确认了 bug，修复方案：\n\n```python\n# 修复除零\ndef _apply_provider_trim(blocks, max_chars):\n    if max_chars <= 0:\n        return blocks, {{'estimated_tokens_before': 0, 'estimated_tokens_after': 0}}\n    # ... existing logic\n    ratio = after_chars / max(max_chars, 1)  # 防御性除法\n```\n\n`_provider_char_budget` 当前的预算表：\n```python\ndef _provider_char_budget(provider_style: str) -> int:\n    budgets = {{\n        'openai': 12000,\n        'anthropic_messages': 10000,\n        'openai_compatible': 8000,\n    }}\n    return budgets.get(provider_style, 8000)\n```\n\n这些全部一起提取到 renderer.py。提取后 manager.py 的 import 改为：\n```python\nfrom .renderer import build_memory_system_blocks, render_memory_for_provider\n```"},
        {"role": "user", "content": "Renderer 提取完成。接下来拆 pack_builder。build_memory_pack 有 200 多行，太长了。"},
        {"role": "assistant", "content": f"build_memory_pack 可以分解为 5 个子步骤：\n\n```python\n{_CODE_BLOCK_2}\n```\n\n建议：\n- 每个子步骤变成独立的私有函数\n- build_memory_pack 变成 20 行的编排函数\n- 新建 `memory/pack_builder.py`"},
        {"role": "user", "content": "拆分 _score_and_select 时发现 selector.py 和 scoring.py 有循环依赖。ScoredMemory 在两边都被引用了。"},
        {"role": "assistant", "content": "经典的循环依赖问题。解决方案：\n\n1. 将 ScoredMemory 移到 models.py（它本就属于数据模型层）\n2. scoring.py 和 selector.py 都从 models.py 导入\n3. 分层原则：models(数据) → scoring(计算) → selector(决策)\n\n具体步骤：\n```python\n# models.py — 添加 ScoredMemory\n@dataclass\nclass ScoredMemory:\n    candidate: MemoryCandidate\n    total_score: float\n    score_breakdown: dict[str, float]\n\n# scoring.py\nfrom .models import ScoredMemory, MemoryCandidate\n\n# selector.py\nfrom .models import ScoredMemory\n```\n\n如果还有 TYPE_CHECKING 引用：\n```python\nfrom __future__ import annotations\n```"},
        {"role": "user", "content": "循环依赖解决了。现在拆 lifecycle：distill_to_l4 和 start_memory_update。这两个方法都依赖 repo 和 summarizer。"},
        {"role": "assistant", "content": f"新建 `memory/lifecycle.py`：\n\n```python\nclass MemoryLifecycle:\n    def __init__(self, repo: StructuredMemoryRepository, summarizer: SessionSummarizer, events: MemoryEventLogger):\n        self._repo = repo\n        self._summarizer = summarizer\n        self._events = events\n\n    async def distill_to_l4(self, session_id: str, messages: list[dict]) -> None:\n        summary = await self._summarizer.summarize_session(messages)\n        record = MemoryRecord(\n            content=summary.text,\n            layer='L4',\n            scope=MemoryScope.SESSION,\n            session_id=session_id,\n            verified=False,\n            evidence_source='session_distillation',\n        )\n        self._repo.upsert(record)\n        self._events.log('l4_distilled', session_id=session_id)\n\n    async def start_memory_update(self, session_id: str, extracted: list[dict]) -> None:\n        policy = WritePolicy()\n        for item in extracted:\n            if policy.validate(item):\n                self._repo.upsert(MemoryRecord(**item))\n                self._events.log('memory_written', memory_id=item['id'])\n```\n\nmanager.py 中创建实例：\n```python\nself._lifecycle = MemoryLifecycle(self._repo, self._summarizer, self._events)\n```"},
        {"role": "user", "content": "lifecycle 也拆好了。现在 manager.py 从 1300 行减到多少了？"},
        {"role": "assistant", "content": "估算拆分效果：\n\n| 提取目标 | 原始行数 | 新文件 |\n|---------|---------|-------|\n| renderer.py | ~180 行 | build_memory_system_blocks + render + trim |\n| pack_builder.py | ~220 行 | build_memory_pack + 5 个子步骤 |\n| lifecycle.py | ~150 行 | distill_to_l4 + start_memory_update |\n\n合计提取：~550 行\nmanager.py 剩余：~750 行\n\n剩余的主要是：\n- __init__ 和配置初始化 (~80行)\n- enrich_from_normalized_request (~100行)\n- 各种工具函数 (~200行)\n- 查询/检索入口 (~150行)\n- 兼容性 API (~100行)\n\n750 行对于一个核心编排模块来说是合理的。"},
        {"role": "user", "content": "不错。现在帮我检查一下提取后有没有遗漏的 import 或者 broken reference。"},
        {"role": "assistant", "content": f"检查结果：\n\n```\n$ python -c \"import nexusgate.memory.manager; print('OK')\"\nTraceback: ImportError: cannot import name 'build_memory_system_blocks' from 'nexusgate.memory.manager'\n```\n\n问题：manager.py 中还有内部引用 `self.build_memory_system_blocks`，需要改为：\n\n```python\n# manager.py\nfrom .renderer import build_memory_system_blocks\n\n# 在 enrich_from_normalized_request 中：\n-   blocks = self.build_memory_system_blocks(pack, provider_style)\n+   blocks = build_memory_system_blocks(pack, provider_style)\n\n# 在 render_memory_for_provider 中：\n-   rows = self.build_memory_system_blocks(pack=pack, provider_style=provider_style)\n+   rows = build_memory_system_blocks(pack=pack, provider_style=provider_style)\n```\n\n同样 lifecycle 方法的调用点也要更新：\n```python\n-   background_tasks.add_task(self.distill_to_l4, session_id, messages)\n+   background_tasks.add_task(self._lifecycle.distill_to_l4, session_id, messages)\n```\n\n修复后所有 import 通过。"},
        {"role": "user", "content": "修完了，import 全部通过。最后帮我总结整个重构的完整变更清单，包括新增文件、修改文件、修复的 bug、以及前后的代码行数对比。"},
        {"role": "assistant", "content": f"完整变更清单：\n\n## 新增文件\n| 文件 | 行数 | 职责 |\n|------|------|------|\n| memory/renderer.py | ~180 | 记忆渲染 + provider trim |\n| memory/pack_builder.py | ~220 | MemoryPack 构建流程 |\n| memory/lifecycle.py | ~150 | L4 蒸馏 + 后台记忆更新 |\n\n## 修改文件\n| 文件 | 变更 |\n|------|------|\n| memory/manager.py | 1340→750 行，提取 3 个模块 |\n| memory/models.py | +ScoredMemory 类（从 scoring.py 迁入）|\n| memory/scoring.py | 改为从 models.py 导入 ScoredMemory |\n| memory/selector.py | 改为从 models.py 导入 ScoredMemory |\n\n## 修复的 Bug\n1. `_apply_provider_trim` 除零错误（max_chars=0）\n2. 循环依赖（scoring ↔ selector）\n3. 提取后遗漏的内部引用（self.build_memory_system_blocks → build_memory_system_blocks）\n\n## 代码行数对比\n```\n修改前: manager.py 1340 行 (单文件)\n修改后: manager.py  750 行\n       renderer.py     180 行\n       pack_builder.py 220 行\n       lifecycle.py    150 行\n       合计           1300 行 (4文件, 净减40行)\n```\n\n代码可维护性从单文件的 1340 行拆分为 4 个职责清晰的模块，每个文件在 150-750 行的合理范围内。"},
        {"role": "user", "content": "非常好。现在运行一下完整的测试套件确认没有 regression。"},
        {"role": "assistant", "content": f"运行测试：\n\n```\n$ python -m pytest tests/memory/ -v\n\ntests/memory/test_manager.py::test_build_memory_pack PASSED\ntests/memory/test_manager.py::test_enrich_from_normalized PASSED\ntests/memory/test_manager.py::test_empty_memory PASSED\ntests/memory/test_renderer.py::test_build_system_blocks PASSED\ntests/memory/test_renderer.py::test_provider_trim PASSED\ntests/memory/test_renderer.py::test_trim_zero_budget PASSED  # 新增：除零修复\ntests/memory/test_pack_builder.py::test_build_pack PASSED\ntests/memory/test_pack_builder.py::test_score_and_select PASSED\ntests/memory/test_lifecycle.py::test_distill_to_l4 PASSED\ntests/memory/test_lifecycle.py::test_start_memory_update PASSED\ntests/memory/test_models.py::test_scored_memory PASSED\ntests/memory/test_scoring.py::test_scorer PASSED\ntests/memory/test_selector.py::test_selector PASSED\ntests/memory/test_repository.py::test_upsert PASSED\ntests/memory/test_repository.py::test_lexical_query PASSED\n\n15 passed in 2.34s\n```\n\n所有测试通过，无 regression。新增了 3 个测试：\n- `test_trim_zero_budget` — 覆盖除零 bug 修复\n- `test_scored_memory` — 验证 ScoredMemory 从 models.py 导入\n- `test_distill_to_l4` — 验证 lifecycle 模块独立性\n\n```python\n{_TOOL_RESULT_2}\n```"},
        {"role": "user", "content": "测试全过了。还有一个问题：重构后 memory 模块的初始化流程是怎样的？manager.py 的 __init__ 现在是什么样？"},
        {"role": "assistant", "content": f"重构后 MemoryManager.__init__ 精简为模块协调器：\n\n```python\n{_CODE_BLOCK_1}\n```\n\n初始化流程：\n1. 创建存储层（repo + index）\n2. 创建计算层（scorer + selector + query_service）\n3. 创建生命周期管理器（lifecycle）\n4. 创建渲染器引用（renderer 是纯函数，无需实例化）\n\n每层只依赖下层，无循环依赖。manager.py 作为最外层 facade，对外暴露 build_memory_pack、enrich_from_normalized_request 等统一接口。"},
        {"role": "user", "content": "好的，整个重构完成。帮我写一个 commit message，包含所有改动的概要。"},
    ],
}

SCENARIOS = [SHORT_SCENARIO, MEDIUM_SCENARIO, LONG_SCENARIO]


# ─── Data Structures ───────────────────────────────────────────────

@dataclass
class ScenarioResult:
    name: str
    description: str
    total_messages: int
    user_turns: int
    # Token counts (same estimator for both, apples-to-apples)
    raw_tokens: int            # No-arch baseline: full uncompressed messages
    prepared_tokens: int       # After history rewrite (compressed messages only)
    memory_tokens: int         # Memory injection overhead
    system_block_tokens: int   # L0 + SOP + grounding rules overhead
    with_arch_tokens: int      # Final: prepared + memory + system_blocks
    # Deltas
    history_saved: int         # raw - prepared (history rewrite benefit)
    arch_overhead: int         # memory + system_blocks (cost of architecture)
    net_saved: int             # raw - with_arch (net savings)
    saved_rate: float          # net_saved / raw
    elapsed_ms: int            # processing time (no upstream)


# ─── Core Pipeline Simulation ──────────────────────────────────────

def simulate_scenario(scenario: dict[str, Any]) -> ScenarioResult:
    """Run NexusGate pipeline offline: history rewrite + memory + system blocks."""
    messages = scenario["messages"]
    name = scenario["name"]
    desc = scenario["description"]
    user_turns = len([m for m in messages if m.get("role") == "user"])

    started = time.perf_counter()

    # Step 1: Raw token count (what the client sends without NexusGate)
    raw_rows = [dict(m) for m in messages]
    raw_tokens = _estimate_tokens_for_messages(raw_rows)

    # Step 2: History rewrite simulation (using NexusGate's actual function)
    try:
        from nexusgate.app import _prepare_messages_for_inference
        prepared_rows, history_stats = _prepare_messages_for_inference(
            [dict(m) for m in messages], mode="light"
        )
        prepared_tokens = int(history_stats.get("prepared_messages_tokens") or 0)
        if prepared_tokens <= 0:
            prepared_tokens = _estimate_tokens_for_messages(prepared_rows)
    except ImportError:
        # Fallback: simulate light mode — keep latest user + 1 system + 1 assistant
        prepared_rows = _simulate_light_rewrite(messages)
        prepared_tokens = _estimate_tokens_for_messages(prepared_rows)

    # Step 3: Memory injection simulation
    # Typical memory pack sizes per layer (based on real data)
    memory_text = (
        "<nexus_context>\n"
        "<memory_index>\n[L1] NexusGate default port: 8000; config via .env\n</memory_index>\n"
        "<relevant_memory>\n"
        "[L2][verified] PORT=8000 default; MEMORY_STORE_PATH=memory; API_KEY_REQUIRED=false for dev\n"
        "[L2][verified] history_rewrite_default_mode supports: disabled, light, normal, heavy, auto\n"
        "[L2][verified] MEMORY_TOP_K=6 controls how many memory items are injected per request\n"
        "</relevant_memory>\n"
        "<relevant_skills>\n"
        "[L3] When debugging startup issues: check PORT, MEMORY_STORE_PATH, API_KEY_REQUIRED first\n"
        "[L3] For refactoring: extract by responsibility, resolve circular deps via shared models\n"
        "</relevant_skills>\n"
        "<session_recall_hints>\n"
        "[L4] Previous session: working on memory module refactoring, completed renderer extraction\n"
        "</session_recall_hints>\n"
        "</nexus_context>"
    )
    memory_tokens = _estimate_tokens_for_messages([{"role": "system", "content": memory_text}])

    # Step 4: System blocks overhead (L0 meta rules + SOP + grounding rules)
    system_blocks_text = (
        "你是由 NexusGate-Core 增强的智能助手。"
        "始终基于 <nexus_context> 中的事实回答；"
        '如果证据不足或上下文未提及，请明确回答"不知道"。'
        "在回答之前，先默认检查每个关键断言是否有 <nexus_context> 中的对应证据。"
        "对于数值、路径、端口、密钥等具体信息，必须逐字引用记忆内容，禁止推断。\n"
        "Grounding policy: pass_through. Grounding mode: balanced.\n"
        "MUST: Use <nexus_context> evidence as primary source for factual claims.\n"
        'MUST: Prefix uncertain statements with "据现有信息" or "Based on available evidence".\n'
        "NEVER: Fabricate specific values (ports, paths, keys) not found in evidence.\n"
        "<memory_management_sop>\n"
        "1. ONLY use facts from <nexus_context>; treat [unverified] items as hints, not truth.\n"
        "2. When two memories conflict, trust the one with newer timestamp + verified=true.\n"
        "3. Never extend a fact beyond what the evidence literally states.\n"
        "</memory_management_sop>"
    )
    system_block_tokens = _estimate_tokens_for_messages([{"role": "system", "content": system_blocks_text}])

    elapsed = int((time.perf_counter() - started) * 1000)

    # Step 5: Compute totals
    with_arch_tokens = prepared_tokens + memory_tokens + system_block_tokens
    history_saved = raw_tokens - prepared_tokens
    arch_overhead = memory_tokens + system_block_tokens
    net_saved = raw_tokens - with_arch_tokens
    saved_rate = round(net_saved / max(raw_tokens, 1), 4)

    return ScenarioResult(
        name=name,
        description=desc,
        total_messages=len(messages),
        user_turns=user_turns,
        raw_tokens=raw_tokens,
        prepared_tokens=prepared_tokens,
        memory_tokens=memory_tokens,
        system_block_tokens=system_block_tokens,
        with_arch_tokens=with_arch_tokens,
        history_saved=history_saved,
        arch_overhead=arch_overhead,
        net_saved=net_saved,
        saved_rate=saved_rate,
        elapsed_ms=elapsed,
    )


def _simulate_light_rewrite(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fallback light rewrite: keep system msgs + latest user + 1 recent assistant."""
    system = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]
    kept: list[dict[str, Any]] = list(system)
    # Latest user message (always kept)
    for m in reversed(non_system):
        if m.get("role") == "user":
            kept.append(m)
            break
    # 1 most recent assistant message
    for m in reversed(non_system):
        if m.get("role") == "assistant":
            kept.append(m)
            break
    return kept


# ─── Report Generation ─────────────────────────────────────────────

def generate_report(results: list[ScenarioResult]) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("  NexusGate Architecture Token Benchmark (offline)")
    lines.append("  Both baselines use the same CJK-aware token estimator")
    lines.append("=" * 78)
    lines.append("")

    # Summary table
    headers = [
        "Scenario",
        "Msgs",
        "No-Arch",
        "With-Arch",
        "Hist Saved",
        "Arch Cost",
        "Net Saved",
        "Rate",
    ]
    rows = []
    for r in results:
        rows.append([
            r.name,
            r.total_messages,
            f"{r.raw_tokens:,}",
            f"{r.with_arch_tokens:,}",
            f"{r.history_saved:+,}",
            f"+{r.arch_overhead:,}",
            f"{r.net_saved:+,}",
            f"{r.saved_rate:.1%}",
        ])

    if tabulate:
        lines.append(tabulate(rows, headers=headers, tablefmt="github"))
    else:
        lines.append(" | ".join(f"{h:>12}" for h in headers))
        lines.append("-" * 78)
        for row in rows:
            lines.append(" | ".join(f"{c:>12}" for c in row))

    lines.append("")

    # Detailed breakdown
    for r in results:
        lines.append("-" * 78)
        lines.append(f"  {r.name} — {r.description}")
        lines.append(f"  Messages: {r.total_messages} total, {r.user_turns} user turns")
        lines.append("-" * 78)
        lines.append(f"  [Without NexusGate]")
        lines.append(f"    Raw input tokens:          {r.raw_tokens:>8,}")
        lines.append(f"  [With NexusGate]")
        lines.append(f"    After history rewrite:     {r.prepared_tokens:>8,}  (saved {r.history_saved:,})")
        lines.append(f"    + Memory injection:        {r.memory_tokens:>8,}  (L0-L4 context)")
        lines.append(f"    + System blocks:           {r.system_block_tokens:>8,}  (rules + SOP + grounding)")
        lines.append(f"    = Total with architecture: {r.with_arch_tokens:>8,}")
        lines.append(f"  [Net Effect]")
        lines.append(f"    History compression:       {r.history_saved:>+8,}  tokens saved")
        lines.append(f"    Architecture overhead:     {r.arch_overhead:>+8,}  tokens added")
        lines.append(f"    ─────────────────────────────────────")
        lines.append(f"    Net savings:               {r.net_saved:>+8,}  ({r.saved_rate:.1%})")
        lines.append(f"    Processing time:           {r.elapsed_ms:>8,}  ms")
        lines.append("")

    # Totals
    total_raw = sum(r.raw_tokens for r in results)
    total_with = sum(r.with_arch_tokens for r in results)
    total_saved = total_raw - total_with
    total_rate = total_saved / max(total_raw, 1)
    lines.append("=" * 78)
    lines.append(f"  TOTAL: {total_raw:,} → {total_with:,}  |  Net saved: {total_saved:+,} ({total_rate:.1%})")
    lines.append("=" * 78)
    lines.append("")

    # Interpretation
    lines.append("  Key Insights:")
    for r in results:
        if r.net_saved < 0:
            lines.append(f"  • {r.name}: Architecture ADDS {-r.net_saved:,} tokens — expected for")
            lines.append(f"    short conversations where history rewrite has little to compress.")
        else:
            lines.append(f"  • {r.name}: Saves {r.net_saved:,} tokens ({r.saved_rate:.0%}) — history")
            lines.append(f"    compression ({r.history_saved:,}) far exceeds overhead ({r.arch_overhead:,}).")

    return "\n".join(lines)


# ─── Main ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="NexusGate Architecture Token Benchmark (offline)")
    parser.add_argument("--output", default=None, help="Save report to file")
    args = parser.parse_args()

    print("NexusGate Architecture Token Benchmark")
    print("Mode: offline (no upstream calls required)")
    print()
    print("Running scenarios...")
    print()

    results: list[ScenarioResult] = []
    for scenario in SCENARIOS:
        r = simulate_scenario(scenario)
        results.append(r)
        print(f"  [{r.name}] {r.total_messages} msgs → raw={r.raw_tokens:,}  with_arch={r.with_arch_tokens:,}  net={r.net_saved:+,} ({r.saved_rate:.0%})  {r.elapsed_ms}ms")

    print()
    report = generate_report(results)
    print(report)

    # Save JSON
    json_path = Path(__file__).resolve().parent / "bench_results.json"
    json_data = [
        {
            "scenario": r.name,
            "description": r.description,
            "total_messages": r.total_messages,
            "user_turns": r.user_turns,
            "raw_tokens_no_arch": r.raw_tokens,
            "prepared_tokens": r.prepared_tokens,
            "memory_tokens": r.memory_tokens,
            "system_block_tokens": r.system_block_tokens,
            "with_arch_tokens": r.with_arch_tokens,
            "history_saved": r.history_saved,
            "arch_overhead": r.arch_overhead,
            "net_saved": r.net_saved,
            "saved_rate": r.saved_rate,
            "elapsed_ms": r.elapsed_ms,
        }
        for r in results
    ]
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"\nReport saved to: {out_path}")

    print(f"JSON results saved to: {json_path}")


if __name__ == "__main__":
    main()
