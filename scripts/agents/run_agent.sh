#!/bin/bash

set -euo pipefail

# Always run from this script's directory
cd "$(cd "$(dirname "$0")" && pwd)"

# Repository root (two levels up from scripts/agents)
REPO_ROOT="$(cd "$(dirname "$0")"/../.. && pwd)"

# Activate venv if present
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
    . "$REPO_ROOT/.venv/bin/activate"
fi

# Load environment variables
set -a
if [ -f "$REPO_ROOT/.env" ]; then
    . "$REPO_ROOT/.env"
fi
set +a

# Defaults (override via env or CLI vars if desired)
AGENT_ID="${AGENT_ID:-aide/claude-sonnet-4-5}"
COMP_SET="${COMP_SET:-$REPO_ROOT/experiments/splits/freiburg-groceries.txt}"
N_WORKERS="${N_WORKERS:-1}"
N_SEEDS="${N_SEEDS:-1}"

# If a competition id is passed as the first argument, use its split file
if [ "${1:-}" != "" ]; then
    COMP_ID="$1"
    COMP_SET="$REPO_ROOT/experiments/splits/${COMP_ID}.txt"
fi

# Basic check to help catch typos
if [ ! -f "$COMP_SET" ]; then
    echo "Error: competition set file not found: $COMP_SET" >&2
    exit 1
fi

python "$REPO_ROOT/run_agent.py" \
  --agent-id "$AGENT_ID" \
  --competition-set "$COMP_SET" \
  --n-workers "$N_WORKERS" \
  --n-seeds "$N_SEEDS"


