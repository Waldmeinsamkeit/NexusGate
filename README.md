# NexusGate

具备本地记忆能力的 LLM 网关，提供 OpenAI 兼容接口，并在请求转发到上游模型前执行记忆检索、筛选、编排与受控写入。

> 适合本地部署给 CLI、编码代理、自动化脚本或兼容 OpenAI API 的客户端使用。

---

## 功能特性

- 统一网关入口，兼容多种客户端接入方式
- 支持以下 API：
  - `POST /v1/chat/completions`
  - `POST /v1/responses`
  - `POST /v1/messages`
- 在上游补全前执行本地记忆检索与上下文注入
- 分层记忆设计，区分稳定事实、可复用技能与会话归档
- 支持官方模型提供方与 OpenAI 兼容第三方后端
- 对高层记忆写入设置更严格的校验门禁
- 适合作为本地“带记忆的模型入口层”

---

## 工作方式

NexusGate 的核心流程如下：

```text
Client
  -> NexusGate
    -> 请求标准化
    -> 记忆检索 / 评分 / 去重 / 组装
    -> 安全与事实约束处理
    -> 转发到上游模型
    -> 异步触发记忆更新 / 会话归档
```

对于 `/v1/responses` 路由，当配置了第三方 OpenAI 兼容上游时，会尽量保持原始透传，以减少对 Codex 工具调用语义的破坏，例如：

- 编辑文件
- 执行命令
- 多轮 tool loop
- 响应流式事件格式保真

---

## 记忆分层设计

当前实现中的记忆语义可概括为：

### L1 — 索引指针
用于存放简短的主题提示、导航线索或路由提示。

适合：
- 关键词索引
- 轻量主题指针
- 简短入口提示

不适合：
- 冗长总结
- 步骤型流程说明

### L2 — 已验证的稳定事实
用于存放可长期复用、且已经验证的具体事实。

适合：
- 已确认的配置项
- 文件路径
- 成功命令
- 端口、模型名、接口行为等稳定结论

不适合：
- 普通闲聊内容
- 泛化摘要
- 未验证信息

### L3 — 可复用任务结论 / 技能
用于存放在编码、调试、重复任务中可复用的方法和经验。

适合：
- 修复模式
- 调试套路
- 稳定工作流结论
- 任务级操作经验

### L4 — 会话回溯 / 归档
用于承载会话摘要、回溯上下文和归档型材料。

特点：
- 是当前会话回顾与压缩的主要承载层
- 某些不适合进入 L2/L3 的内容，会以压缩归档形式进入这一层

---

## 记忆写入原则

当前写入策略是偏保守的：

- **L1 / L2 / L3 应以 verified 内容为主**
- **L4 可以存储会话摘要与归档材料**
- **L2 不存放泛化的会话总结**
- **L1 不存放步骤化长流程**
- 高层记忆在写入前会经过更严格的规则门禁

这样做的目标是：

- 提高检索稳定性
- 减少跨层污染
- 避免“把临时对话误当长期事实”

---

## 记忆选择与组装

请求进入网关后，记忆并不是简单地“固定 top-k 拼接”，而是经过更清晰的选择流程：

1. **任务分类**
   - 识别当前请求更接近 coding、debugging、planning、retrieval 或 general chat

2. **预算分配**
   - 按任务类型分配不同的记忆预算

3. **候选评分**
   - 综合多种信号排序，例如：
     - term overlap
     - task-type preference
     - layer weight
     - verification status

4. **跨层去重**
   - 去掉同一事实的低价值重复版本

5. **最终组装**
   - 形成发往上游模型的 memory context

---

## 支持的上游模式

NexusGate 可以将请求路由到：

### 1) 官方模型提供方
例如：

- OpenAI
- Anthropic

### 2) OpenAI 兼容第三方后端
例如：

- LiteLLM Proxy
- Bifrost
- 其他 OpenAI-compatible 聚合服务

如果设置了第三方 `TARGET_BASE_URL`，网关会优先使用该上游地址。

---

## 项目结构

典型入口如下：

- 应用工厂：`nexusgate.app:create_app`
- 默认启动模块：`nexus_gate_core:app`

---

## 安装

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd NexusGate
```

### 2. 安装依赖

```bash
python -m pip install -r requirements.txt
```

当前依赖包括：

- `fastapi`
- `uvicorn`
- `litellm`
- `pydantic`
- `pydantic-settings`
- `chromadb`
- `sentence-transformers`

---

## 配置

建议先复制示例配置：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

### `.env.example` 主要配置项

```env
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

APP_NAME=NexusGate-Core
APP_ENV=dev
HOST=0.0.0.0
PORT=8000
REQUEST_TIMEOUT_SECONDS=120

LOCAL_API_KEY=ng-abc123
API_KEY_REQUIRED=false
LOCAL_API_KEY_STORE_PATH=~/.nexusgate/secrets.json

CLIENT_SYNC_ENABLED=true
CODEX_CONFIG_PATH=C:/Users/Administrator/.codex/config.toml
CLAUDE_SETTINGS_PATH=C:/Users/Administrator/.claude/settings.json
CODEX_LOCAL_BASE_URL=http://127.0.0.1:8000/v1
CLAUDE_LOCAL_BASE_URL=http://127.0.0.1:8000

UPSTREAM_API_KEY_REQUIRED=true
DEFAULT_MODEL=claude-sonnet-4-5-20250929

TARGET_PROVIDER=gpt-5.3-codex
TARGET_BASE_URL=https://your-openai-compatible-endpoint/v1
TARGET_API_KEY=sk-upstream-xxx

LLMAPI_BASE_URL=
LLMAPI_API_KEY=
LLMAPI_MODEL_PREFIX=llmapi/
LLMAPI_PROVIDER_PREFIX=openai/

MEMORY_ENABLED=true
MEMORY_STORE_PATH=memory
MEMORY_SOURCE_ROOT=.
MEMORY_COLLECTION_NAME=nexusgate_memory
MEMORY_TOP_K=6
```

### 关键配置说明

#### 网关监听
- `HOST`：监听地址
- `PORT`：监听端口

#### 本地鉴权
- `LOCAL_API_KEY`：客户端访问 NexusGate 时使用的本地密钥
- `API_KEY_REQUIRED`：是否要求请求携带 Bearer Token
- 如果设置了 `LOCAL_API_KEY`，请求需携带相同 token

#### 上游模型
- `TARGET_PROVIDER`：目标模型名或默认上游模型
- `TARGET_BASE_URL`：第三方 OpenAI 兼容上游地址
- `TARGET_API_KEY`：第三方上游密钥

#### 兼容旧字段
以下字段仍可作为兼容别名参与解析：

- `LLMAPI_BASE_URL`
- `LLMAPI_API_KEY`

#### 记忆系统
- `MEMORY_ENABLED`：是否启用记忆
- `MEMORY_STORE_PATH`：本地记忆目录
- `MEMORY_SOURCE_ROOT`：源码/工作目录根路径
- `MEMORY_COLLECTION_NAME`：记忆集合名称
- `MEMORY_TOP_K`：默认检索数量

---

## 启动方式

### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

### Windows PowerShell

```powershell
./run.ps1
```

### 直接使用 uvicorn

```bash
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

也可以使用工厂风格入口自行组织启动：

```bash
python -m uvicorn nexusgate.app:create_app --factory --host 0.0.0.0 --port 8000
```

---

## 常见部署场景

### 场景 A：转发到官方模型

```bash
export TARGET_PROVIDER=claude-sonnet-4-5-20250929
export ANTHROPIC_API_KEY=sk-ant-xxx
export OPENAI_API_KEY=sk-xxx
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

### 场景 B：转发到 OpenAI 兼容第三方后端

```bash
export TARGET_PROVIDER=gpt-5.3-codex
export TARGET_BASE_URL=http://localhost:11434/v1
export TARGET_API_KEY=sk-anything
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

---

## API 入口

### 1) Chat Completions

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

### 2) Responses API

```bash
curl http://127.0.0.1:8000/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ng-abc123" \
  -d '{
    "model": "gpt-5.3-codex",
    "input": "检查当前仓库的 README 是否与实现一致"
  }'
```

### 3) Anthropic-style Messages

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

> 本地鉴权支持以下头部之一：
>
> - `Authorization: Bearer <token>`
> - `x-api-key: <token>`
> - `api-key: <token>`

---

## 客户端接入

### OpenAI 兼容客户端

- **Base URL:** `http://127.0.0.1:8000/v1`
- **Model:** 使用你希望路由的模型名
- **API Key:** 若启用了本地鉴权，则填 `LOCAL_API_KEY`

### Aider 示例

```bash
aider \
  --model claude-sonnet-4-5-20250929 \
  --api-base http://127.0.0.1:8000/v1
```

### Codex / Claude 本地配置

配置中已经预留：

- `CODEX_CONFIG_PATH`
- `CLAUDE_SETTINGS_PATH`
- `CODEX_LOCAL_BASE_URL`
- `CLAUDE_LOCAL_BASE_URL`

用于将本地工具指向 NexusGate。

---

## 健康检查

```bash
curl http://127.0.0.1:8000/health
```

---

## 测试

已验证的单元测试命令示例：

```bash
PYTHONPATH=. python -m unittest discover -s tests -p "test_memory_manager.py"
```

在当前仓库环境中，该组 memory manager 测试已通过：

- `Ran 16 tests`
- `OK`

---

## 当前状态

当前代码库已经不再只是一个“简单的记忆注入网关”，而是更接近一个本地记忆增强的模型入口层：

- selector / scoring / policy 逻辑已做更清晰拆分
- 高层记忆写入门禁更严格
- L4 继续承担会话回溯与归档主职责
- `/v1/responses` 对 OpenAI 兼容上游优先采用保真透传策略
- 文档正在逐步与真实实现语义对齐

---

## 适用场景

- 本地 coding agent 网关
- 给 CLI 工具增加会话记忆
- 给 OpenAI 兼容客户端统一接入多个上游
- 对代理任务保留任务级经验与历史上下文
- 在本地实现“受控写入”的长期记忆层

---

## 参考

- [GenericAgent](https://github.com/lsdefine/GenericAgent)  
  记忆架构思路参考来源之一

- [LiteLLM](https://github.com/BerriAI/litellm)  
  用于兼容多种上游模型与 OpenAI-compatible 后端

---

## License

本项目包含 `LICENSE` 文件，请按仓库中的实际许可证使用。