#!/bin/bash

# Script to download custom_data from GCS bucket (only missing files)
# Usage: ./download_custom_data.sh

set -e  # Exit on any error

BUCKET_PATH="gs://internal-llm-rnd/mle-bench/turing-tasks"
# Resolve repository root even when called from elsewhere
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEST_DIR="$REPO_ROOT/custom_data"

echo "Starting sync from $BUCKET_PATH to $DEST_DIR"

# Check if gsutil is available
if ! command -v gsutil &> /dev/null; then
    echo "Error: gsutil is not installed or not in PATH"
    echo "Please install Google Cloud SDK and authenticate with 'gcloud auth login'"
    exit 1
fi

# Check if user is authenticated
if ! gsutil ls gs://internal-llm-rnd &> /dev/null; then
    echo "Error: Not authenticated with Google Cloud or bucket doesn't exist"
    echo "Please run 'gcloud auth login' and ensure you have access to the bucket"
    exit 1
fi

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

echo "Syncing all objects recursively (unchanged files will be skipped)..."
gsutil -m rsync -r -c "$BUCKET_PATH" "$DEST_DIR"

echo "Sync completed! All objects under $BUCKET_PATH are mirrored to $DEST_DIR."
