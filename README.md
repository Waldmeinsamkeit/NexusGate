# NexusGate-Core

本地中转网关：统一对外 OpenAI 兼容接口（`/v1/chat/completions`），内部执行记忆召回后，再转发到官方或第三方上游 LLM。

## 功能

- 单一入口：`POST /v1/chat/completions`
- 五层记忆（最小可移植子集）：L0/L1/L2/L4
- 上游转发：
  - 官方模型（OpenAI / Anthropic）
  - 第三方 OpenAI 兼容聚合器（LiteLLM Proxy / Bifrost / 其他）

## 安装

```bash
python -m pip install -r requirements.txt
```

## 环境变量

可复制 `.env.example` 并填写：

```env
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

TARGET_PROVIDER=claude-sonnet-4-5-20250929
TARGET_BASE_URL=
TARGET_API_KEY=

MEMORY_SOURCE_ROOT=F:/repo/GenericAgent
MEMORY_STORE_PATH=memory
MEMORY_USE_CHROMA=false
```

说明：
- 当 `TARGET_BASE_URL` 为空时，走官方模型路由（`TARGET_PROVIDER`）。
- 当 `TARGET_BASE_URL` 非空时，优先转发到第三方聚合器。
- `MEMORY_USE_CHROMA=true` 时启用 Chroma 持久化；默认关闭以避免本机环境兼容性问题。

## 启动

```bash
# Linux / macOS
chmod +x run.sh && ./run.sh

# Windows PowerShell
./run.ps1
```

## 两种中转场景

### 场景 A：转发官方 Claude / Codex

```bash
export TARGET_PROVIDER=claude-sonnet-4-5-20250929
export ANTHROPIC_API_KEY=sk-ant-xxx
export OPENAI_API_KEY=sk-xxx
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

### 场景 B：转发外部 LLM API 聚合器
```bash
export TARGET_BASE_URL=http://localhost:11434/v1
export TARGET_API_KEY=sk-anything
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

## 客户端统一配置

- Base URL: `http://localhost:8000/v1`
- API Key: `sk-anything`（默认不校验）
- Model: `claude-sonnet-4-5-20250929` 或 `gpt-5.2-codex`

示例：
```bash
aider --model claude-sonnet-4-5-20250929 --api-base http://localhost:8000/v1
```

## 健康检查
```bash
curl http://127.0.0.1:8000/health
```
