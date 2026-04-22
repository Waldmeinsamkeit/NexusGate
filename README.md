# NexusGate

NexusGate 是一个本地可部署的 LLM 网关，提供 OpenAI 兼容接口，并在请求转发前后执行：

- 记忆检索与上下文注入
- Provider 路由与失败回退
- 上下文裁剪与重渲染
- 基于证据的 grounding 与幻觉抑制
- 本地 API Key 管理与客户端配置同步

## 核心接口

- `POST /v1/chat/completions`
- `POST /v1/responses`
- `POST /v1/messages`
- `GET /health`

## 目录结构（当前）

后端核心代码已统一迁移到 `back/`：

```text
back/
  nexusgate/
  nexus_gate_core.py
tests/
memory/
```

仓库根目录保留了兼容入口（shim）：

- `nexus_gate_core.py`（转发到 `back.nexus_gate_core`）
- `nexusgate/__init__.py`（兼容 `import nexusgate.*`）

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制示例配置：

```bash
cp .env.example .env
```

常用变量（示例）：

```env
APP_NAME=NexusGate-Core
HOST=0.0.0.0
PORT=8000

LOCAL_API_KEY=ng-abc123
API_KEY_REQUIRED=false

TARGET_PROVIDER=gpt-5.3-codex
TARGET_BASE_URL=
TARGET_API_KEY=

MEMORY_ENABLED=true
MEMORY_STORE_PATH=memory
MEMORY_SOURCE_ROOT=.
MEMORY_TOP_K=6
```

## 启动

推荐（应用工厂）：

```bash
python -m uvicorn back.nexusgate.app:create_app --factory --host 0.0.0.0 --port 8000
```

兼容入口：

```bash
python -m uvicorn back.nexus_gate_core:app --host 0.0.0.0 --port 8000
```

也可使用脚本：

- `run.ps1`
- `run.sh`

## 调用示例

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ng-abc123" \
  -d '{
    "model": "gpt-5.3-codex",
    "messages": [{"role": "user", "content": "请总结当前项目的启动方式"}]
  }'
```

## 测试

```bash
python -m pytest -q
```

或执行常用回归集：

```bash
$memoryTests = Get-ChildItem tests -Filter "test_memory_*.py" | ForEach-Object { $_.FullName }; python -m pytest @memoryTests tests/test_provider_router.py tests/test_app_phase_a.py tests/test_app_phase_bcd.py -q
```

## License

见 `LICENSE`。

