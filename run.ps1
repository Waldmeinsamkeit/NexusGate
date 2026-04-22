$ErrorActionPreference = "Stop"

if (-not $env:OPENAI_API_KEY) { $env:OPENAI_API_KEY = "sk-xxx" }
if (-not $env:ANTHROPIC_API_KEY) { $env:ANTHROPIC_API_KEY = "sk-ant-xxx" }
if (-not $env:TARGET_PROVIDER) { $env:TARGET_PROVIDER = "claude-sonnet-4-5-20250929" }
# if (-not $env:TARGET_BASE_URL) { $env:TARGET_BASE_URL = "http://localhost:11434/v1" }
# if (-not $env:TARGET_API_KEY) { $env:TARGET_API_KEY = "sk-anything" }
# if (-not $env:GROQ_API_KEY) { $env:GROQ_API_KEY = "gsk_xxx" }

python -m uvicorn back.nexus_gate_core:app --host 0.0.0.0 --port 8000

