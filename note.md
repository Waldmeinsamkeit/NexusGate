› 告诉我如何测试


• 1. 安装依赖

  cd F:\repo\NexusGate
  python -m pip install -r requirements.txt

  2. 配置 .env（二选一）

  场景 A：转发官方

  TARGET_PROVIDER=claude-sonnet-4-5-20250929
  OPENAI_API_KEY=sk-xxx
  ANTHROPIC_API_KEY=sk-ant-xxx
  MEMORY_SOURCE_ROOT=F:/repo/GenericAgent
  MEMORY_USE_CHROMA=false

  场景 B：转发第三方聚合器

  TARGET_BASE_URL=http://localhost:11434/v1
  TARGET_API_KEY=sk-anything
  MEMORY_SOURCE_ROOT=F:/repo/GenericAgent
  MEMORY_USE_CHROMA=false

  3. 启动服务

  .\run.ps1

  4. 健康检查

  curl http://127.0.0.1:8000/health

  期望：status=ok，upstream 显示当前上游（TARGET_BASE_URL 或 TARGET_PROVIDER）。

  5. 非流式转发测试

  $body = @{
    model = "claude-sonnet-4-5-20250929"
    session_id = "test-s1"
    stream = $false
    temperature = 0.3
    messages = @(
      @{ role="user"; content="请回复：中转成功" }
    )
  } | ConvertTo-Json -Depth 10

  curl -X POST "http://127.0.0.1:8000/v1/chat/completions" `
    -H "Content-Type: application/json" `
    -H "Authorization: Bearer sk-anything" `
    -d $body

  期望：返回 choices[0].message.content；如果上游 key/网络异常会返回 502。

  6. 流式测试

  $body = @{
    model = "claude-sonnet-4-5-20250929"
    session_id = "test-stream"
    stream = $true
    messages = @(
      @{ role="user"; content="用三行说明你是谁" }
    )
  } | ConvertTo-Json -Depth 10

  curl -N -X POST "http://127.0.0.1:8000/v1/chat/completions" `
    -H "Content-Type: application/json" `
    -d $body

  期望：持续输出 SSE 数据块。

  7. 记忆写入验证（L4）
     先发两轮同一 session_id 请求，再检查：

  - F:\repo\NexusGate\memory\global_mem_insight.txt
  - F:\repo\NexusGate\memory\global_mem.txt

  再用同一 session_id 发第三轮，观察回答是否引用前文事实（说明召回生效）。

  8. 代码级回归测试

  python -m unittest tests.test_memory_manager tests.test_gateway -v

  期望：Ran 6 tests ... OK。

  如果你要，我可以再给你一个 smoke_test.ps1，一键跑完 4-8 步并输出通过/失败摘要。