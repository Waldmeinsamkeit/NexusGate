
# 🌌 NexusGate

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**NexusGate** 是一个具备高度定制化与记忆增强能力的本地 LLM（大语言模型）API 网关。

它就像运行在您本地的 **"Cloudflare for LLMs"**。作为统一接入层，NexusGate 可以无缝代理各类 AI 应用（如 Cursor、Aider、自动化 Agent 等）的流量，在请求到达 OpenAI 或 Anthropic 之前，智能地完成**本地记忆注入**、**跨模型路由调度**、**动态上下文压缩**以及**幻觉抑制**。

---

## ✨ 核心特性 (Core Features)

### 🧠 分层记忆系统 (Tiered MemoryPack)
告别简单粗暴的 RAG 拼接。NexusGate 将本地知识划分为五大语义层，精准控制大模型的上下文注意力：
- **L0 (元规则)**：全局系统约束，绝对遵循的底层逻辑。
- **L1=Constraints (约束)**：代码规范、环境要求、索引约定。
- **L2=Facts (事实)**：基于当前请求动态检索（Top-K）的业务知识。
- **L3=Procedures (技能)**：可复用的 SOP 与标准操作步骤。
- **L4=Continuity (连续性)**：维持长会话状态的任务线索。

## 注入原理：
运行时不会把全部长期记忆直接拼接进上下文，而是先按请求进行分层检索、相关性排序、验证过滤与语义压缩，再按提供商预算进行裁剪后注入。其中 `L4` 默认只在调试、规划或出现连续性查询信号时纳入，因而整体机制更接近“分层检索 + 小包注入”，而不是“全量 RAG 拼接”。

### 🔄 智能提供商感知渲染 (Provider-Aware Rendering)
无论上游接入的是什么模型，NexusGate 都会自动将记忆包“翻译”成最契合该模型的底层语法。例如，对于 OpenAI 链路渲染为 `<memory_index>`，而对于 Claude 链路则自动转换为 `<anthropic_relevant_skills>`，最大化指令遵从度。

### ✂️ 动态上下文压缩 (Dynamic Compression)
突破 Token 限制！内置**预算感知裁剪算法**，当会话上下文溢出时，网关不会报错，而是根据优先级（保留 L0，裁剪边缘事实）智能压缩上下文并重试，保障流水线 100% 稳定运行。

### 🛡️ 幻觉抑制与降级重试 (Grounding & Fallback)
自带防幻觉防火墙。网关会强制要求模型基于证据块（Evidence Blocks）作答，自动校验无支撑声明比例（Unsupported Ratio）。一旦发现模型胡编乱造，立即拦截并触发重写或向备用模型降级（Fallback Chain）。

---

## 🏗️ 架构模式 (Architecture)

NexusGate 支持完全兼容 OpenAI 规范的 API 接口 (`/v1/chat/completions`)，支持以下部署拓扑：

- **模式 A (直连增强)**：`Client -> NexusGate (记忆注入) -> OpenAI/Anthropic 官方 API`
- **模式 B (本地/聚合嵌套)**：`Client -> NexusGate (审查与调度) -> Ollama / vLLM / 第三方聚合 API`

---

## 🚀 快速开始 (Getting Started)

### 环境要求
- Python 3.9 或更高版本
- 建议使用虚拟环境 (venv 或 conda)

### 1. 安装
```bash
# 克隆仓库
git clone https://github.com/Waldmeinsamkeit/NexusGate.git
cd NexusGate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
在项目根目录创建 `.env` 文件，并配置您的密钥与存储参数：

```env
# 核心网关配置
GATEWAY_PORT=8000
GATEWAY_HOST=0.0.0.0

# 记忆向量库配置 (本地存储)
MEMORY_STORE_PATH=./memory
MEMORY_COLLECTION_NAME=nexusgate_memory
MEMORY_TOP_K=6

# 提供商 API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
```

### 3. 启动服务
您可以使用内置脚本一键启动，网关将默认在 `http://localhost:8000` 运行：
```bash
# Linux / macOS
./run.sh

# Windows
.\run.ps1
```
> **提示**: 您也可以通过浏览器访问 `http://localhost:8000/admin/ui` 进入可视化的管理面板 (Dashboard)。

---

## 💻 接入示例 (Usage)

启动 NexusGate 后，您只需将现有 AI 客户端的 `Base URL` 指向本地网关即可，无需修改任何业务代码。

**Python (OpenAI SDK) 示例:**

```python
from openai import OpenAI

# 将 base_url 指向本地的 NexusGate
client = OpenAI(
    api_key="your-proxy-key-or-any-string", 
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="claude-3-5-sonnet", # 哪怕调用 Claude 也可以使用 OpenAI SDK
    messages=[
        {"role": "user", "content": "检查一下这段代码是否符合我们的团队规范？"}
    ]
)

print(response.choices[0].message.content)
```

**IDE 插件 (如 Cursor/Aider) 配置:**
在插件设置中，覆盖默认的 API Base 为 `http://localhost:8000/v1`，NexusGate 即可自动接管编程过程中的错误记忆与团队代码规范注入。

---

## 📂 项目结构 (Project Structure)

```text
NexusGate/
├── nexusgate/          # 后端核心代码 (FastAPI)
│   ├── app.py          # ASGI 应用工厂
│   ├── router/         # Provider 路由与 Fallback 逻辑
│   ├── memory/         # 核心！MemoryPack 结构与本地向量库检索
│   └── interceptors/   # 防幻觉校验与流量拦截器
├── front/              # Web Dashboard 前端界面 (HTML/JS/CSS)
├── memory/             # 本地持久化的知识与向量数据 (运行时生成)
├── run.sh              # 启动脚本
└── requirements.txt    # 依赖清单
```

---

## 🤝 参与贡献 (Contributing)

我们欢迎任何形式的贡献！如果您有新的想法、发现了 Bug 或希望增加对新 Provider 的支持，请遵循以下流程：
1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 将分支推送到远程 (`git push origin feature/AmazingFeature`)
5. 发起 Pull Request

## 📄 许可证 (License)

本项目采用 [MIT License](LICENSE) 许可协议开源。您可以自由地使用、修改和分发代码。禁止用于商业用途。