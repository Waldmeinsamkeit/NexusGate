$ErrorActionPreference = "Stop"

if (-not $env:OPENAI_API_KEY) { $env:OPENAI_API_KEY = "sk-xxx" }
if (-not $env:ANTHROPIC_API_KEY) { $env:ANTHROPIC_API_KEY = "sk-ant-xxx" }
# if (-not $env:GROQ_API_KEY) { $env:GROQ_API_KEY = "gsk_xxx" }

python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000

