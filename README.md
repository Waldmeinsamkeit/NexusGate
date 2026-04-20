# NexusGate-Core

统一 OpenAI 兼容入口（`/v1/chat/completions`）+ 内嵌 LiteLLM 聚合网关。

## 核心能力

- 对外只暴露 `POST /v1/chat/completions`
- 内部通过 `litellm.completion()` 适配 OpenAI/Anthropic 等模型
- 五层记忆最小可移植子集（L0/L1/L2/L4）已接入
- 支持第三方 OpenAI 兼容站点（通过 `llmapi/` 模型前缀路由）

## 快速启动

1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

2. 配置环境变量（可复制 `.env.example`）

```env
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

DEFAULT_MODEL=claude-sonnet-4-5-20250929
MEMORY_SOURCE_ROOT=F:/repo/GenericAgent
```

3. 启动

```bash
# Linux / macOS
chmod +x run.sh && ./run.sh

# Windows PowerShell
./run.ps1
```

## 第三方 LLM API 站点接入

在 `.env` 中配置：

```env
LLMAPI_BASE_URL=https://your-llmapi-site/v1
LLMAPI_API_KEY=sk-your-third-party-key
LLMAPI_MODEL_PREFIX=llmapi/
LLMAPI_PROVIDER_PREFIX=openai/
```

然后客户端请求时把 `model` 写成 `llmapi/<模型名>`，例如：

- `llmapi/gpt-4o-mini`
- `llmapi/deepseek-v3`

网关会自动转换为 LiteLLM 调用参数：

- `model` -> `openai/<模型名>`
- `api_base` -> `LLMAPI_BASE_URL`
- `api_key` -> `LLMAPI_API_KEY`

## 客户端通用配置

- Base URL: `http://localhost:8000/v1`
- API Key: 任意值（默认不校验）
- Model: 任一支持模型名

## 记忆存储

- 默认优先使用 ChromaDB（`memory/chroma`）
- 若环境无 `chromadb`，自动回退到进程内内存存储

