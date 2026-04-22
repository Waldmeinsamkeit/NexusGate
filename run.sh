#!/usr/bin/env bash
set -euo pipefail

export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-xxx}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-sk-ant-xxx}"
export TARGET_PROVIDER="${TARGET_PROVIDER:-claude-sonnet-4-5-20250929}"
# export TARGET_BASE_URL="http://localhost:11434/v1"
# export TARGET_API_KEY="sk-anything"
# export GROQ_API_KEY="${GROQ_API_KEY:-gsk_xxx}"

exec python -m uvicorn back.nexus_gate_core:app --host 0.0.0.0 --port 8000

