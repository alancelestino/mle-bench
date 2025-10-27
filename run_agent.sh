#!/bin/bash

set -euo pipefail

# Always run from this script's directory
cd "$(cd "$(dirname "$0")" && pwd)"

# Activate venv (absolute path)
if [ -f /home/alan_celestino/mle-bench/.venv/bin/activate ]; then
    source /home/alan_celestino/mle-bench/.venv/bin/activate
fi

# Load environment variables
set -a
source /home/alan_celestino/mle-bench/.env
set +a

# Defaults (override via env or CLI vars if desired)
AGENT_ID="${AGENT_ID:-aide/claude-sonnet-4-5}"
COMP_SET="${COMP_SET:-/home/alan_celestino/mle-bench/experiments/splits/freiburg-groceries.txt}"
N_WORKERS="${N_WORKERS:-1}"
N_SEEDS="${N_SEEDS:-1}"

python /home/alan_celestino/mle-bench/run_agent.py \
  --agent-id "$AGENT_ID" \
  --competition-set "$COMP_SET" \
  --n-workers "$N_WORKERS" \
  --n-seeds "$N_SEEDS"


