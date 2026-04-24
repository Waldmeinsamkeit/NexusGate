﻿<p align="center">
  <h1 align="center">NexusGate</h1>
  <p align="center">
    Memory-augmented local LLM API gateway — <em>"Cloudflare for LLMs"</em>
    <br />
    <a href="#-quick-start"><strong>Quick Start »</strong></a>
    &nbsp;&middot;&nbsp;
    <a href="#-best-practices"><strong>Best Practices »</strong></a>
    &nbsp;&middot;&nbsp;
    <a href="#-architecture"><strong>Architecture »</strong></a>
  </p>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.100+-00a393.svg" alt="FastAPI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="http://makeapullrequest.com"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

---

**NexusGate** is a local LLM API gateway with built-in layered memory, cross-model routing, dynamic context compression, and hallucination suppression.

It sits between your AI clients (Cursor, Codex CLI, Aider, custom agents…) and upstream LLM providers (OpenAI, Anthropic, Ollama, etc.), transparently enriching every request with local knowledge before it leaves your machine.

> **一句话概括**：在 AI 请求到达云端之前，自动注入本地记忆、压缩上下文、抑制幻觉——零代码改动，即插即用。

## Table of Contents

- [Why NexusGate](#-why-nexusgate)
- [Core Features](#-core-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Best Practices](#-best-practices)
- [Project Structure](#-project-structure)
- [Configuration Reference](#-configuration-reference)
- [API Endpoints](#-api-endpoints)
- [Contributing](#-contributing)
- [License](#-license)

## 💡 Why NexusGate

| Problem | How NexusGate solves it |
|---------|----------------------|
| Models forget prior decisions in long sessions | Five-layer memory system (L0–L4) injects verified context every turn |
| Token waste on redundant history | Intelligent history rewrite + tool-result compression |
| Hallucinated ports, paths, config values | Evidence-based grounding check + structured `MUST/NEVER` rules |
| Locked into one provider | Unified OpenAI-compatible API with multi-provider routing & fallback |
| No visibility into gateway behavior | Admin dashboard with request tracing, memory browser, token stats |

### Best-fit scenarios

- Multi-turn debugging / refactoring sessions
- Cross-file call-chain analysis
- Long document / log summarization
- Tasks requiring persistent user preferences, project constraints, or incremental conclusions

<<<<<<< HEAD
---
## NexusGate 最适合的使用场景

它最有价值的场景是：

- 长对话、多轮推进的任务
- 复杂代码排错
- 跨多个文件的调用链分析
- 分阶段重构
- 长文档/长日志总结
- 需要持续保留“用户偏好、项目约束、阶段结论”的任务

不太需要它深度介入的场景：

- 一次性很短的小问题
- 完全不依赖上下文的单轮问答
- 与之前任务无关的临时问题
---
=======
### Not necessary for
>>>>>>> 3b3d94a1e9c993e93662fb9b1e813518645c37ce

- One-off short questions
- Context-free single-turn Q&A

## ✨ Core Features

### Tiered Memory System (L0–L4)

Not a naive RAG paste. NexusGate classifies local knowledge into five semantic layers, each with its own token budget, validation rules, and injection policy:

| Layer | Name | Purpose | Max chars | Injection |
|-------|------|---------|-----------|-----------|
| **L0** | Meta Rules | Immutable system constraints (SOP) | — | Always |
| **L1** | Constraints | Index pointers, env requirements | 96 | Always |
| **L2** | Facts | Verified business knowledge (Top-K retrieval) | 240 | By relevance |
| **L3** | Procedures | Reusable SOP / task takeaways | 240 | By task type |
| **L4** | Continuity | Session archive for long tasks | 600 | Debug / planning / on trigger |

**How injection works:**
1. Classify the incoming query (debug / coding / planning / chat)
2. Retrieve candidates via hybrid search (vector + lexical)
3. Score, deduplicate, resolve conflicts, filter stale/unverified entries
4. Allocate token budget per layer based on task type
5. Render with provider-specific formatting (XML for Claude, Markdown for GPT)

### Provider-Aware Rendering

System blocks are automatically formatted for the target model:

- **Claude** → XML tags (`<nexus_rules>`, `<verified_facts>`, `<grounding>`, …)
- **GPT** → Markdown headings (`## Core Rules`, `## Verified Facts`, …)
- **Others** → Plain text (backward-compatible)

### Dynamic Context Compression

When context exceeds the model's window, NexusGate applies a three-pass budget:

1. **Truncate** long system blocks
2. **Drop** low-priority system blocks
3. **Trim** older assistant/tool messages (never drops the latest user message)

Combined with **tool-result compression** (consecutive tool messages collapsed) and **CJK-aware token estimation**, this keeps requests within budget without silent failures.

### Token Savings Measurement

NexusGate includes a built-in token counter that compares actual usage against a **correct baseline** — what the client would send directly to the provider without NexusGate:

```
Baseline (no architecture) = raw uncompressed client messages
With architecture          = compressed history + memory injection + system blocks
Savings                    = baseline - actual sent
```

Token logs are written to `solo_token.txt` per request, with an aggregate summary in `memory/sum_memory.txt` including overall `saved_rate`.

Offline benchmark results (`scripts/arch_token_benchmark.py`):

| Scenario | Messages | No-Arch | With-Arch | Net Saved | Rate |
|----------|----------|---------|-----------|-----------|------|
| Short (1-turn) | 1 | 20 | 542 | -522 | N/A |
| Medium (10-turn) | 10 | 1,356 | 579 | +777 | **57%** |
| Long (30-turn) | 23 | 5,494 | 565 | +4,929 | **90%** |

- **Short conversations**: Architecture adds overhead (memory + system blocks ~524 tokens) with nothing to compress — this is expected and honest.
- **Medium conversations**: History compression outweighs overhead, net positive savings.
- **Long conversations**: Savings of **90%** as history rewrite aggressively compresses accumulated context while injecting only relevant memory slices.

### Grounding & Hallucination Guard

Post-response safety pipeline:

1. **Split** response into individual claims
2. **Extract** key-value entities (port, path, URL, version, …)
3. **Verify** each entity against source evidence using structured pattern matching + n-gram overlap
4. **Degrade** if unsupported: `pass_through` → `attach_warning` → `degrade_uncertainty` → `strip_unsupported` → `retry_with_stricter_grounding`

When memory `verified_ratio > 90%`, grounding rules automatically shorten to a single line, saving tokens.

### Smart Routing & Fallback

Multi-factor model selection considering quality tier, cost, health (circuit breaker), task type, tool support, and risk profile. Automatic fallback chain on upstream failures with classified recovery actions (context overflow → trim & retry, tool schema mismatch → disable tools, transient → backoff retry).

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Clients: Cursor · Codex CLI · Aider · Custom Agent · Browser   │
└────────────────────────┬─────────────────────────────────────────┘
                         │  OpenAI-compatible API
                         ▼
┌──────────────────── NexusGate ───────────────────────────────────┐
│                                                                  │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │ API Key │→ │ Normalize│→ │ History  │→ │  Memory Pack    │  │
│  │ Validate│  │ Request  │  │ Rewrite  │  │  Build & Select │  │
│  └─────────┘  └──────────┘  └──────────┘  └────────┬────────┘  │
│                                                     │           │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────▼────────┐  │
│  │   Provider   │← │  Prompt Plan  │← │  System Blocks       │  │
│  │   Router     │  │  + Budget Trim│  │  (L0+SOP+Grounding+  │  │
│  └──────┬───────┘  └───────────────┘  │   Evidence+Citations)│  │
│         │                             └──────────────────────┘  │
│         ▼                                                       │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │   Upstream   │→ │  Grounding    │→ │  Background Tasks    │  │
│  │   Call       │  │  Guard        │  │  (L4 distill, memory │  │
│  │  + Fallback  │  │  + Degrade    │  │   update, token log) │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  Providers: OpenAI · Anthropic · Ollama · vLLM · OpenRouter     │
└──────────────────────────────────────────────────────────────────┘
```

**Deployment modes:**
- **Mode A (Direct):** `Client → NexusGate → OpenAI / Anthropic API`
- **Mode B (Aggregated):** `Client → NexusGate → Ollama / vLLM / third-party aggregator`

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- (Recommended) Virtual environment via `venv` or `conda`

### 1. Install

```bash
git clone https://github.com/Waldmeinsamkeit/NexusGate.git
cd NexusGate
pip install -r requirements.txt
```

### 2. Configure

<<<<<<< HEAD
```env
# 核心网关配置
APP_ENV=dev
HOST=0.0.0.0
PORT=8000

# 记忆向量库配置 (本地存储)
MEMORY_ENABLED=true
MEMORY_STORE_PATH=memory
MEMORY_COLLECTION_NAME=nexusgate_memory
MEMORY_TOP_K=6

# 提供商 API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# 历史替代模式开关（light / normal / heavy / auto）
HISTORY_REWRITE_ENABLED=true
HISTORY_REWRITE_DEFAULT_MODE=auto
HISTORY_REWRITE_GLOBAL_LIGHT_QUERY_THRESHOLD=120

# light 模式
HISTORY_REWRITE_LIGHT_KEEP_SYSTEM=0
HISTORY_REWRITE_LIGHT_KEEP_USER=1
HISTORY_REWRITE_LIGHT_KEEP_ASSISTANT=0
HISTORY_REWRITE_LIGHT_KEEP_TOOL=0
HISTORY_REWRITE_LIGHT_KEEP_OTHER=0
HISTORY_REWRITE_LIGHT_MAX_CHARS_PER_MESSAGE=700

# normal 模式
HISTORY_REWRITE_NORMAL_KEEP_SYSTEM=1
HISTORY_REWRITE_NORMAL_KEEP_USER=1
HISTORY_REWRITE_NORMAL_KEEP_ASSISTANT=1
HISTORY_REWRITE_NORMAL_KEEP_TOOL=1
HISTORY_REWRITE_NORMAL_KEEP_OTHER=0
HISTORY_REWRITE_NORMAL_MAX_CHARS_PER_MESSAGE=1200

# heavy 模式
HISTORY_REWRITE_HEAVY_KEEP_SYSTEM=1
HISTORY_REWRITE_HEAVY_KEEP_USER=2
HISTORY_REWRITE_HEAVY_KEEP_ASSISTANT=1
HISTORY_REWRITE_HEAVY_KEEP_TOOL=2
HISTORY_REWRITE_HEAVY_KEEP_OTHER=1
HISTORY_REWRITE_HEAVY_MAX_CHARS_PER_MESSAGE=1800

# 全局上下文预算器（Phase D）
CONTEXT_BUDGET_ENABLED=true
CONTEXT_BUDGET_RESPONSE_RESERVE_RATIO=0.3
CONTEXT_BUDGET_MIN_PROMPT_TOKENS=512
```

> 建议：先复制 `.env.example` 为 `.env` 再按需调整。默认推荐 `HISTORY_REWRITE_DEFAULT_MODE=auto`。

### 3. 启动服务
您可以使用内置脚本一键启动，网关将默认在 `http://localhost:8000` 运行：
=======
```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# ── Provider keys ──────────────────────────
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# ── Gateway ────────────────────────────────
HOST=0.0.0.0
PORT=8000
TARGET_PROVIDER=claude-sonnet-4-5-20250929

# ── Memory ─────────────────────────────────
MEMORY_ENABLED=true
MEMORY_STORE_PATH=memory
MEMORY_TOP_K=6

# ── Client sync (auto-configure IDE plugins)
CLIENT_SYNC_ENABLED=true
```

> See [Configuration Reference](#-configuration-reference) for all 40+ options.

### 3. Start

>>>>>>> 3b3d94a1e9c993e93662fb9b1e813518645c37ce
```bash
# Linux / macOS
./run.sh

# Windows (PowerShell)
.\run.ps1
```

The gateway is now running at `http://localhost:8000`. Visit `http://localhost:8000/admin/ui` for the admin dashboard.

## 💻 Usage

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-local-key",        # or any string if API_KEY_REQUIRED=false
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="claude-sonnet-4-5-20250929",  # cross-provider via OpenAI SDK
    messages=[
        {"role": "user", "content": "Check if this code follows our team conventions."}
    ]
)
print(response.choices[0].message.content)
```

### IDE Integration

| Tool | Setting | Value |
|------|---------|-------|
| **Cursor** | `openai.apiBase` | `http://localhost:8000/v1` |
| **Codex CLI** | Auto-configured if `CLIENT_SYNC_ENABLED=true` | — |
| **Claude Code** | Auto-configured if `CLIENT_SYNC_ENABLED=true` | — |
| **Aider** | `--openai-api-base` | `http://localhost:8000/v1` |
| **Custom Agent** | Set `base_url` in your SDK client | `http://localhost:8000/v1` |

### Supported API Styles

NexusGate accepts three API formats and normalizes them internally:

| Endpoint | Style | Use case |
|----------|-------|----------|
| `POST /v1/chat/completions` | OpenAI Chat | Default for most clients |
| `POST /v1/responses` | OpenAI Responses | Codex CLI passthrough |
| `POST /v1/messages` | Anthropic Messages | Claude-native clients |

## 🎯 Best Practices

### How to ask questions effectively

NexusGate works best when you provide structured information that it can store and reuse. Here are proven patterns:

#### 1. Seed your preferences (stored as L1/L2)

```
Remember my preferences:
- Evidence before conclusions
- Read source code before modifying
- Respond in Chinese
- Include file paths and line numbers
- Prefer no-code-change solutions first
```
<<<<<<< HEAD
---
### NexusGate 的作用

它在两者之间负责：

- 记住前几轮的关键结论
- 压缩长任务里的上下文
- 把用户偏好、项目约束、阶段成果重新注入后续轮次
- 降低模型在长任务中的遗忘和漂移
---
## 想让 NexusGate 更好提取记忆，应该主动告诉它什么

### 1. 用户偏好
例如：
`记住我的偏好： - 先证据后结论 - 修改前先读源码 - 尽量中文回答 - 回答带文件路径和行号 - 能不改代码就先不改`

### 2. 项目级约束

例如：
`这个项目的固定约束： - 默认不联网 - 优先读日志再看源码 - 所有改动都要可回滚 - 不要碰生产配置`

### 3. 已确认的稳定事实
例如：
`当前已确认事实： - 后端入口在 back/nexusgate/app.py - 配置在 back/nexusgate/config.py - 内存索引在 back/nexusgate/memory/index.py`

模板：
```
将项目结构分类导入L2，索引到L1中
```
---
## 🤝 参与贡献 (Contributing)
=======

#### 2. Define project constraints (stored as L1)

```
Project constraints:
- No internet access by default
- Read logs before source code
- All changes must be reversible
- Never touch production config
```
>>>>>>> 3b3d94a1e9c993e93662fb9b1e813518645c37ce

#### 3. Import project facts (stored as L2)

```
Confirmed facts:
- Backend entry: back/nexusgate/app.py
- Config: back/nexusgate/config.py
- Memory index: back/nexusgate/memory/index.py
- Frontend: React + Vite in front/

<<<<<<< HEAD
本项目采用 [MIT License](LICENSE) 许可协议开源。您可以自由地使用、修改和分发代码。禁止用于商业用途。
=======
Import the above as L2 facts and index them in L1.
```

#### 4. End-of-task memory extraction

Append this at the end of each task to let NexusGate extract reusable knowledge:

```
Classify verified reusable information from this session:
- L2: environment facts
- L3: task experience / SOP
- L4 only: session-specific context
If L2/L3 candidates exist, update long-term memory first, then summarize.
```

#### 5. Session resume

When returning to a previous task:

```
Continue from where we left off.
```

NexusGate will automatically inject L4 session archive and recovered state (goal, constraints, decisions, completed work, blockers, next step).

### Tips for reducing token usage

- **Short greetings** ("hi", "hello") skip the memory pipeline automatically
- Set `HISTORY_REWRITE_DEFAULT_MODE=auto` to let NexusGate compress history based on task complexity
- For simple questions that don't need memory, add `skip_memory: true` in request metadata
- Check `memory/sum_memory.txt` for aggregate token savings stats (`saved_rate`, `saved_total_tokens`)

### Tips for reducing hallucination

- **Verify facts before storing**: Only confirmed information should go into L2
- **Use structured queries**: "What port does service X run on?" is better than "Tell me about the setup"
- **Check `[unverified]` tags**: NexusGate marks low-confidence memories; treat them as hints, not facts

## 📂 Project Structure

```
NexusGate/
├── back/nexusgate/             # Backend core (FastAPI)
│   ├── app.py                  # ASGI app factory + all API endpoints
│   ├── config.py               # 40+ config fields via pydantic-settings
│   ├── gateway.py              # LiteLLM gateway wrapper
│   ├── schemas.py              # Request/response Pydantic models
│   ├── local_proxy.py          # API key management + IDE client sync
│   ├── prompt_policies.py      # SOP blocks + session recall injection
│   ├── memory/                 # Five-layer memory system
│   │   ├── manager.py          # MemoryManager (build, enrich, render, distill)
│   │   ├── repository.py       # JSONL-backed persistent storage
│   │   ├── index.py            # ChromaDB vector index + NullIndex fallback
│   │   ├── query_service.py    # Hybrid search (vector + lexical + scorer)
│   │   ├── scoring.py          # Multi-factor relevance scoring
│   │   ├── selector.py         # Task classification + budget-aware selection
│   │   ├── write_policy.py     # Validation, staleness, noise filtering
│   │   └── summarizer.py       # Fact extraction + session summary
│   ├── prompting/              # Prompt plan construction
│   │   ├── plan.py             # NormalizedPromptPlan builder
│   │   ├── system_blocks.py    # Dedup, merge, provider-aware rendering
│   │   ├── renderers.py        # Render to messages or responses payload
│   │   └── preparer.py         # Final prompt preparation + budget trim
│   ├── router/                 # Provider routing
│   │   ├── provider_router.py  # Multi-factor scoring + fallback
│   │   ├── capability_registry.py  # Model capabilities registry
│   │   └── provider_health.py  # Circuit breaker + latency tracking
│   └── safety/                 # Hallucination suppression
│       └── grounding.py        # Claim splitting, entity check, guard
├── front/                      # Admin dashboard (React + TypeScript + Vite)
│   └── src/
│       ├── App.tsx             # Tab-based SPA
│       └── components/         # Dashboard, Memory, Tracing, Settings, ...
├── memory/                     # Runtime memory storage (auto-generated)
├── .env.example                # Configuration template
├── requirements.txt            # Python dependencies
├── run.sh                      # Start script (Linux/macOS)
└── run.ps1                     # Start script (Windows)
```

## ⚙️ Configuration Reference

Key settings in `.env` (full list in `back/nexusgate/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `TARGET_PROVIDER` | `claude-sonnet-4-5-20250929` | Default upstream model |
| `TARGET_BASE_URL` | — | Custom OpenAI-compatible endpoint |
| `TARGET_API_KEY` | — | API key for custom endpoint |
| `API_KEY_REQUIRED` | `false` | Require local API key for clients |
| `LOCAL_API_KEY` | — | Gateway API key (auto-generated if empty) |
| `CLIENT_SYNC_ENABLED` | `true` | Auto-configure Codex CLI / Claude Code |
| `MEMORY_ENABLED` | `true` | Enable memory system |
| `MEMORY_STORE_PATH` | `memory` | Local memory storage path |
| `MEMORY_TOP_K` | `6` | Top-K results per memory query |
| `MEMORY_USE_CHROMA` | `false` | Use ChromaDB vector index |
| `HISTORY_REWRITE_DEFAULT_MODE` | `auto` | History compression: `auto` / `light` / `normal` / `heavy` / `disabled` |
| `CONTEXT_BUDGET_ENABLED` | `true` | Enable context budget trimming |
| `CONTEXT_BUDGET_RESPONSE_RESERVE_RATIO` | `0.3` | Reserve ratio for model response |

## 🔌 API Endpoints

### LLM Proxy

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat/completions` | OpenAI Chat Completions (main entry) |
| `POST` | `/v1/responses` | OpenAI Responses API (Codex CLI) |
| `POST` | `/v1/messages` | Anthropic Messages API |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/admin/config` | View current configuration |
| `PUT` | `/admin/config` | Update configuration |
| `GET` | `/admin/traces` | Request trace history |
| `GET` | `/admin/memories` | Query memory records |
| `POST` | `/admin/memories` | Create memory record |
| `PUT` | `/admin/memories/{id}` | Update memory record |
| `DELETE` | `/admin/memories/{id}` | Archive memory record |

Admin dashboard: `http://localhost:8000/admin/ui`

## 🤝 Contributing

Contributions are welcome! Please follow this flow:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

[MIT License](LICENSE) — Copyright (c) 2026 Waldmeinsamkeit
>>>>>>> 3b3d94a1e9c993e93662fb9b1e813518645c37ce
