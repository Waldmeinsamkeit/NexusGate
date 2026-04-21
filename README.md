# NexusGate-Core

具备本地记忆能力的 LLM 网关，提供 OpenAI 兼容 API。

NexusGate 对外暴露统一的 `/v1/chat/completions` 接口，在请求转发到上游模型前先执行记忆检索与编排，然后再转发到官方模型提供方或 OpenAI 兼容的第三方后端。

## 功能概览

- OpenAI 兼容入口：`POST /v1/chat/completions`
- 在上游补全前执行基于记忆的请求编排
- 分层记忆设计，兼顾检索与受控写入
- 支持官方模型提供方与 OpenAI 兼容聚合后端
- 适合 CLI 工具与编码代理的本地部署

## 架构概览

```text
Client
  -> NexusGate (/v1/chat/completions)
    -> memory query / ranking / dedupe / assembly
    -> upstream forwarding
      -> OpenAI / Anthropic / compatible proxy
```

## 记忆层级

NexusGate 采用分层记忆模型。当前更符合实际实现的语义如下：

- **L1 — 索引指针**
  - 用于存放简短的路由提示或主题指针
  - 作为轻量级导航线索使用
  - 不适合存放流程步骤或长篇总结

- **L2 — 已验证的稳定事实**
  - 可长期复用、且足够具体的事实信息
  - 适合存放已验证的配置、文件位置、端口、成功结果及其他稳定结论
  - 普通会话闲聊不应写入这一层

- **L3 — 可复用任务结论 / 技能**
  - 可重复使用的实现模式或任务级经验
  - 更适合编码、调试和重复性工作流

- **L4 — 会话回溯 / 归档**
  - 用于存放会话摘要、回溯上下文和归档型记忆
  - 即使某些内容不适合进入 L2/L3，也可以压缩后存入这一层

## 记忆写入规则

当前写入策略刻意保持保守：

- **L1 / L2 / L3 必须是 verified 内容**
- **L4 可以存储会话摘要与归档材料**
- **L2 不存放通用型会话摘要**
- **L1 不存放逐步流程说明**
- 高层记忆在提交前会经过校验规则门禁

这样可以让检索质量更稳定，并减少跨层污染。

## 选择策略

记忆选择不再只是固定预算裁剪。当前流程更接近：

1. **任务分类**
   - 判断当前请求更接近 coding、debugging、planning、retrieval 还是 general chat

2. **预算分配**
   - 按任务类型分配不同的记忆预算

3. **排序**
   - 基于 term overlap、task-type preference、layer weight、verification status 等信号为候选项打分

4. **跨层去重**
   - 去除同一事实的重复版本或价值更低的变体

5. **裁剪与组装**
   - 生成最终发往上游模型调用的 memory header

## 上游路由

NexusGate 可以将请求转发到：

- **官方模型**
  - OpenAI
  - Anthropic

- **OpenAI 兼容的第三方后端**
  - LiteLLM Proxy
  - Bifrost
  - 其他兼容聚合器

## 项目参考
https://github.com/lsdefine/GenericAgent (提取了记忆架构)

litellm (用于兼容 OpenAI 兼容聚合后端) 


## 安装

```bash
python -m pip install -r requirements.txt
```

## 环境变量

可以复制 `.env.example` 并填写对应值：

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

- 如果 `TARGET_BASE_URL` 为空，NexusGate 会按 `TARGET_PROVIDER` 指定的官方提供方路由请求。
- 如果设置了 `TARGET_BASE_URL`，NexusGate 会优先将请求转发到该兼容上游端点。
- `MEMORY_USE_CHROMA=true` 会启用基于 Chroma 的持久化；默认关闭，以避免本地环境兼容性问题。

## 运行

```bash
# Linux / macOS
chmod +x run.sh && ./run.sh

# Windows PowerShell
./run.ps1
```

也可以直接启动：

```bash
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

## 示例场景

### 场景 A：转发到官方 Claude / Codex

```bash
export TARGET_PROVIDER=claude-sonnet-4-5-20250929
export ANTHROPIC_API_KEY=sk-ant-xxx
export OPENAI_API_KEY=sk-xxx
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

### 场景 B：转发到外部 OpenAI 兼容聚合后端

```bash
export TARGET_BASE_URL=http://localhost:11434/v1
export TARGET_API_KEY=sk-anything
python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000
```

## 客户端配置

- **Base URL:** `http://localhost:8000/v1`
- **API Key:** 如果未启用本地鉴权，默认可使用 `sk-anything`
- **Model:** `claude-sonnet-4-5-20250929` 或 `gpt-5.2-codex`

示例：

```bash
aider --model claude-sonnet-4-5-20250929 --api-base http://localhost:8000/v1
```

## 健康检查

```bash
curl http://127.0.0.1:8000/health
```

## 当前状态

当前代码库已经不再只是一个简单的记忆注入网关：

- selector / scoring / policy 逻辑已经做了更清晰的拆分
- 高层记忆写入门禁已经更严格
- L4 仍然是会话回溯与归档行为的主要承载层
- 文档正在继续补齐，以与真实实现语义保持一致
