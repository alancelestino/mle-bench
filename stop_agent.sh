#!/bin/bash

set -euo pipefail

# Always run from this script's directory
cd "$(cd "$(dirname "$0")" && pwd)"

# Load environment variables (if present in repo root)
set -a
if [ -f "$PWD/.env" ]; then
    source "$PWD/.env"
fi
set +a

# Accept optional competition id and agent id
COMP_ID="${1:-${COMP_ID:-freiburg-groceries}}"
AGENT_ID="${AGENT_ID:-aide/claude-sonnet-4-5}"

# Kill host-side runners and log tails
pkill -f "run_agent.py.*${AGENT_ID}" || true
pkill -f "tail -n 0 -f .*${COMP_ID}_.*/run.log" || true

# Remove competition containers
docker ps -a --format "{{.ID}} {{.Names}}" | awk -v cid="$COMP_ID" '$2 ~ ("competition-" cid) {print $1}' | xargs -r docker rm -f || true

echo "Stopped runs for $COMP_ID and removed matching containers."


