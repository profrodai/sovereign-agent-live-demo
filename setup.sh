#!/usr/bin/env bash
# One-time setup for the live Sovereign Agent demo.
# Safe to re-run. It creates a local uv-managed environment and pulls an Ollama model.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> 1/4  Checking uv ..."
if ! command -v uv >/dev/null 2>&1; then
  echo "    ERROR: 'uv' not found. Install it first:"
  echo "      curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "    (or: brew install uv)  Docs: https://docs.astral.sh/uv/"
  exit 1
fi
echo "    using: $(uv --version)"

echo "==> 2/4  Installing sovereign-agent + zeocore from PyPI (uv supplies Python 3.14) ..."
uv sync
echo "    installed:"
uv pip list 2>/dev/null | grep -Ei 'sovereign-agent|zeocore' || true

echo "==> 3/4  Checking Ollama ..."
if ! command -v ollama >/dev/null 2>&1; then
  echo "    ERROR: 'ollama' not found. Install it from https://ollama.com/download"
  exit 1
fi
MODEL="${SOVEREIGN_DEMO_MODEL:-qwen3:latest}"
if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  echo "    pulling model $MODEL (this is a few GB, one time) ..."
  ollama pull "$MODEL"
else
  echo "    model $MODEL already present."
fi

echo "==> 4/4  Warming the model so the live run is fast ..."
printf '' | ollama run "$MODEL" >/dev/null 2>&1 || true

echo
echo "Setup complete. Now run, in order:"
echo "  uv run sovereign-agent demo store --mode simulated   # offline, deterministic"
echo "  uv run python demo_tool_calling.py                   # LIVE: a model calls a tool"
echo "  uv run python demo_full_governance.py                # LIVE: the full governed loop"
