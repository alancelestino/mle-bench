#!/bin/bash

set -euo pipefail

# Always run from this script's directory
cd "$(cd "$(dirname "$0")" && pwd)"

# Load environment variables
set -a
source /home/alan_celestino/mle-bench/.env
set +a

# Kill host-side runners and log tails
pkill -9 -f "run_agent.py.*aide/claude-sonnet-4-5-20250929" || true
pkill -f "tail -n 0 -f .*freiburg-groceries_.*/run.log" || true

# Remove competition containers
docker ps -a --format "{{.ID}} {{.Names}}" | awk '/competition-freiburg-groceries/ {print $1}' | xargs -r docker rm -f || true

echo "Stopped AIDE runs and removed Freiburg containers."


