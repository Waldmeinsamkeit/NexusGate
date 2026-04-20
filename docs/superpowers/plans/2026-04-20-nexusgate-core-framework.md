# NexusGate Core Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建统一 OpenAI 兼容入口，并内嵌 LiteLLM 聚合能力与五层记忆占位框架。

**Architecture:** 使用 FastAPI 暴露 `/v1/chat/completions`，请求进入后先经过 MemoryManager 做消息增强占位，再交给 LiteLLM 统一转发到具体模型提供商。记忆层采用可插拔分层接口，当前以 no-op 实现打通主流程，后续可按层逐步替换。

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, LiteLLM, Pydantic v2

---

### Task 1: FastAPI 统一入口

**Files:**
- Create: `nexus_gate_core.py`
- Create: `nexusgate/app.py`
- Create: `nexusgate/schemas.py`

- [x] **Step 1: 创建 app 入口并暴露路由**
- [x] **Step 2: 实现 `POST /v1/chat/completions` 请求模型与映射**
- [x] **Step 3: 增加 `GET /health` 健康检查**

### Task 2: LiteLLM 聚合网关

**Files:**
- Create: `nexusgate/gateway.py`
- Modify: `nexusgate/app.py`

- [x] **Step 1: 封装 `litellm.completion()` 调用**
- [x] **Step 2: 将请求参数透传至 LiteLLM 并统一返回字典响应**
- [x] **Step 3: 异常映射为 `502 Bad Gateway`**

### Task 3: 五层记忆框架占位

**Files:**
- Create: `nexusgate/memory/layers.py`
- Create: `nexusgate/memory/manager.py`
- Create: `nexusgate/memory/__init__.py`
- Modify: `nexusgate/app.py`

- [x] **Step 1: 定义五层记忆层接口（session/working/episodic/semantic/archive）**
- [x] **Step 2: 定义 `MemoryManager` 串联 enrich/persist 生命周期**
- [x] **Step 3: 接入聊天主链路（请求前 enrich，请求后 persist）**

### Task 4: 启动与配置

**Files:**
- Create: `run.sh`
- Create: `run.ps1`
- Create: `nexusgate/config.py`
- Create: `.env.example`
- Create: `requirements.txt`

- [x] **Step 1: 增加环境变量驱动配置**
- [x] **Step 2: 提供 Linux/macOS 与 Windows 启动脚本**
- [x] **Step 3: 固化最小依赖清单**

### Task 5: 使用文档与定向验证

**Files:**
- Create: `README.md`

- [x] **Step 1: 写明工具侧统一配置方式（Base URL/API Key/Model）**
- [x] **Step 2: 写明常用模型命名示例**
- [x] **Step 3: 执行语法编译与 API smoke test**

