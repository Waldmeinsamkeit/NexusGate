# NexusGate

具备本地记忆能力的 LLM 网关，提供 OpenAI 兼容入口，并在请求转发到上游模型前完成：

- 记忆检索与上下文注入
- 跨 provider 路由与回退
- 动态上下文压缩
- 基于证据的幻觉抑制
- 本地 API Key 管理与客户端配置同步

它适合部署在本地或内网，作为 CLI、Agent、自动化脚本、IDE 插件、OpenAI 兼容客户端的统一接入层。

---

## 1. 核心能力

### 1.1 OpenAI 兼容网关入口

当前支持以下接口：

- `POST /v1/chat/completions`
- `POST /v1/responses`
- `POST /v1/messages`
- `GET /health`

你可以把 NexusGate 当成一个本地 LLM API 聚合入口，对外暴露统一 Base URL，再由它决定记忆注入、路由、回退和安全控制。

---

### 1.2 分层记忆系统

NexusGate 会围绕请求构建 `MemoryPack`，并将记忆分为稳定结构后再渲染到不同 provider：

- `L0`：全局元规则 / 系统级约束
- `constraints`：约束、规则、索引类信息
- `procedures`：技能、步骤、可复用操作经验
- `continuity`：会话连续性线索、任务上下文
- `facts`：与当前任务相关的事实记忆

在注入模型前，系统会按 provider 风格渲染记忆：

- OpenAI 风格标签：
  - `<memory_index>`
  - `<relevant_skills>`
  - `<session_recall_hints>`
  - `<relevant_memory>`

- Anthropic Messages 风格标签：
  - `<anthropic_memory_index>`
  - `<anthropic_relevant_skills>`
  - `<anthropic_session_recall_hints>`
  - `<anthropic_relevant_memory>`

---

### 1.3 动态上下文压缩

NexusGate 不是简单地“把所有记忆都塞进去”，而是会根据 provider 的上下文预算执行裁剪：

- 先构建标准化 render blocks
- 再执行 provider-aware trim
- 保留 canonical section 结构
- 生成 `trim_report`
- 在上下文溢出时优先进行 rerender / trim retry，而不是盲目失败

这让它更适合长对话、长任务、代理式工作流。

---

### 1.4 跨 provider 路由与回退

NexusGate 内置 `ProviderRouter`，可根据配置与请求特征进行路由，并在失败时回退。

当前实现具备这些行为：

- 根据目标模型或上游配置决定 provider
- 支持 direct provider 与 OpenAI-compatible backend 两种模式
- 支持 fallback chain
- 支持同 provider 重试
- 支持上下文溢出后的 rerender trim retry
- 支持工具模式不兼容时降级重试
- 记录 provider 健康信息与部分回退事件

---

### 1.5 幻觉抑制与 grounding

在请求发往上游前，NexusGate 会附加 grounding 规则与证据块；在回答阶段，可结合支持性检查抑制幻觉。

当前已实现的安全相关能力包括：

- 基于记忆事实与约束构建 evidence blocks
- 通过 citation block 约束回答引用依据
- 基于 claim support 进行检查
- 输出 `unsupported_ratio`
- 对 unsupported claims 执行 rewrite / degrade 策略
- 在严格模式或高风险情况下更保守回答
- 通过系统提示要求“未知就说不知道”

这让网关更适合知识型问答、项目辅助、代理执行等容易出现“编造答案”的场景。

---

## 2. 运行模式

NexusGate 支持两类上游模式。

### 模式 A：直连 provider

例如直连某个 provider 的模型：

- `TARGET_PROVIDER=claude-sonnet-4-5-20250929`
- 同时配置对应 provider 所需 API Key

### 模式 B：转发到 OpenAI 兼容后端

例如转发到自建聚合层、本地模型服务、第三方兼容接口：

- `TARGET_PROVIDER=gpt-5.3-codex`
- `TARGET_BASE_URL=http://localhost:11434/v1`
- `TARGET_API_KEY=sk-anything`

如果配置了 `TARGET_BASE_URL`，NexusGate 会以 OpenAI-compatible 模式请求上游。

---

## 3. 安装

### 3.1 环境要求

- Python 3.10+
- 可访问的上游模型服务或 OpenAI-compatible 接口

### 3.2 安装依赖

```bash
pip install -r requirements.txt
```

---

## 4. 配置

项目根目录提供了 `.env.example`，可复制为 `.env` 后修改。

```bash
cp .env.example .env
```

### 4.1 基础配置

```env
APP_NAME=NexusGate-Core
APP_ENV=dev
HOST=0.0.0.0
PORT=8000
REQUEST_TIMEOUT_SECONDS=120
```

### 4.2 本地鉴权

```env
LOCAL_API_KEY=ng-abc123
API_KEY_REQUIRED=false
LOCAL_API_KEY_STORE_PATH=~/.nexusgate/secrets.json
```

支持以下请求头之一：

- `Authorization: Bearer <token>`
- `x-api-key: <token>`
- `api-key: <token>`

---

### 4.3 上游 provider / OpenAI-compatible 配置

```env
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

TARGET_PROVIDER=gpt-5.3-codex
TARGET_BASE_URL=https://your-openai-compatible-endpoint/v1
TARGET_API_KEY=sk-upstream-xxx
UPSTREAM_API_KEY_REQUIRED=true
DEFAULT_MODEL=claude-sonnet-4-5-20250929
```

字段说明：

- `TARGET_PROVIDER`：默认目标模型或 provider 入口
- `TARGET_BASE_URL`：上游 OpenAI-compatible 接口地址；留空则走 provider direct 模式
- `TARGET_API_KEY`：上游接口所需密钥
- `DEFAULT_MODEL`：默认模型名
- `UPSTREAM_API_KEY_REQUIRED`：是否强制要求上游 key

---

### 4.4 LLMAPI 兼容字段（legacy aliases）

为兼容旧配置，当前仍保留：

```env
LLMAPI_BASE_URL=
LLMAPI_API_KEY=
LLMAPI_MODEL_PREFIX=llmapi/
LLMAPI_PROVIDER_PREFIX=openai/
```

建议新部署优先使用：

- `TARGET_BASE_URL`
- `TARGET_API_KEY`
- `TARGET_PROVIDER`

如果你前端里要做“LLMAPI 的 API / Base URL 配置”，建议 UI 层这样处理：

- 主展示名：`OpenAI-Compatible Upstream`
- 兼容导入名：`LLMAPI (Legacy)`
- 保存时统一写入 `TARGET_*`
- 如检测到旧字段存在，则在界面中提示“已从 legacy alias 导入”

---

### 4.5 记忆配置

```env
MEMORY_ENABLED=true
MEMORY_STORE_PATH=memory
MEMORY_SOURCE_ROOT=.
MEMORY_COLLECTION_NAME=nexusgate_memory
MEMORY_TOP_K=6
```

字段说明：

- `MEMORY_ENABLED`：是否启用记忆增强
- `MEMORY_STORE_PATH`：本地记忆存储路径
- `MEMORY_SOURCE_ROOT`：源代码 / 工作目录根路径
- `MEMORY_COLLECTION_NAME`：记忆集合名
- `MEMORY_TOP_K`：每次检索的记忆条数上限

---

### 4.6 本地客户端同步配置

```env
CLIENT_SYNC_ENABLED=true
CODEX_CONFIG_PATH=C:/Users/Administrator/.codex/config.toml
CLAUDE_SETTINGS_PATH=C:/Users/Administrator/.claude/settings.json
CODEX_LOCAL_BASE_URL=http://127.0.0.1:8000/v1
CLAUDE_LOCAL_BASE_URL=http://127.0.0.1:8000
```

用于把本地工具自动指向 NexusGate。

---

## 5. 启动

### 5.1 使用应用工厂启动

```bash
python -m uvicorn nexusgate.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 5.2 兼容旧启动方式

仓库中也保留了旧示例：

```bash
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

如新版本以 `nexusgate.app:create_app` 为准，建议优先采用应用工厂方式启动。

---

## 6. API 示例

### 6.1 Chat Completions

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ng-abc123" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "messages": [
      {"role": "user", "content": "帮我总结当前项目的启动方式"}
    ]
  }'
```

### 6.2 Responses API

```bash
curl http://127.0.0.1:8000/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ng-abc123" \
  -d '{
    "model": "gpt-5.3-codex",
    "input": "检查当前仓库的 README 是否与实现一致"
  }'
```

### 6.3 Anthropic-style Messages

```bash
curl http://127.0.0.1:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: ng-abc123" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 512,
    "messages": [
      {"role": "user", "content": "解释一下这个项目的记忆分层"}
    ]
  }'
```

---

## 7. 客户端接入

### 7.1 OpenAI 兼容客户端

- **Base URL**: `http://127.0.0.1:8000/v1`
- **Model**: 你希望路由到的模型名
- **API Key**: 如果启用了本地鉴权，则填写 `LOCAL_API_KEY`

### 7.2 Aider

```bash
aider \
  --model claude-sonnet-4-5-20250929 \
  --api-base http://127.0.0.1:8000/v1
```

### 7.3 Codex / Claude 本地配置

可结合以下配置项自动接入：

- `CODEX_CONFIG_PATH`
- `CLAUDE_SETTINGS_PATH`
- `CODEX_LOCAL_BASE_URL`
- `CLAUDE_LOCAL_BASE_URL`

---

## 8. 健康检查

```bash
curl http://127.0.0.1:8000/health
```

典型返回信息包含：

- `status`
- `upstream`
- `upstream_mode`
- `auth_mode`
- `local_key_source`
- `sync_status`
- `synced_clients`
- `sync_errors`

这对于前端管理台很有用，可以直接做“系统状态总览”。

---

## 9. 当前实现重点

基于当前代码，README 需要明确：它已经不只是一个“记忆拼接器”，而是一个具备多层控制逻辑的本地网关：

- 有分层记忆与 provider-aware render
- 有动态裁剪与 trim report
- 有路由、回退、同 provider 重试
- 有 grounding 与幻觉抑制
- 有本地 key 与客户端同步能力
- 有 OpenAI-compatible 与 provider-direct 双模式

---

## 10. 测试

可按仓库内测试继续验证关键能力，例如：

```bash
PYTHONPATH=. python -m unittest discover -s tests -p "test_memory_manager.py"
```

建议后续补充的测试方向：

- 路由决策测试
- fallback trace 测试
- grounding rewrite 测试
- OpenAI-compatible upstream 测试
- 管理台 API 测试

---

## 11. 适用场景

- 本地 coding agent 网关
- 带记忆的 CLI / IDE 助手
- 多模型统一接入层
- 企业内部知识增强问答入口
- 有审计与安全要求的代理执行环境

---

## 12. License

本项目包含 `LICENSE` 文件，请按仓库中的实际许可证使用
未经允许，任何组织和个人不得用于商业用途。