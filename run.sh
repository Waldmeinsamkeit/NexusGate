#!/usr/bin/env bash
set -euo pipefail

export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-xxx}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-sk-ant-xxx}"
# export GROQ_API_KEY="${GROQ_API_KEY:-gsk_xxx}"

exec python -m uvicorn nexus_gate_core:app --host 0.0.0.0 --port 8000

