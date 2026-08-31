#!/usr/bin/env bash
# One-time setup for the live Sovereign Agent demo.
# Safe to re-run. It only creates a local .venv and pulls an Ollama model.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> 1/4  Checking Python 3.14 ..."
PY=""
for c in python3.14 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,14) else 1)'; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "    ERROR: Python 3.14+ not found. sovereign-agent 1.0.0 requires it."
  echo "    Install it from https://www.python.org/downloads/  (or: pyenv install 3.14.3)"
  exit 1
fi
echo "    using: $($PY --version)"

echo "==> 2/4  Creating .venv and installing sovereign-agent + zeocore from PyPI ..."
"$PY" -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt
echo "    installed:"
./.venv/bin/pip list 2>/dev/null | grep -Ei 'sovereign-agent|zeocore' || true

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
echo "  ./.venv/bin/sovereign-agent demo store --mode simulated   # offline, deterministic"
echo "  ./.venv/bin/python demo_tool_calling.py                   # LIVE: a model calls a tool"
echo "  ./.venv/bin/python demo_full_governance.py                # LIVE: the full governed loop"
