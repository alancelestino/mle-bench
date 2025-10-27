#!/bin/bash

# Script to upload custom_data directory contents to GCS bucket
# Usage: ./upload_custom_data.sh

set -e  # Exit on any error

BUCKET_PATH="gs://internal-llm-rnd/mle-bench/turing-tasks"
# Resolve repository root even when called from elsewhere
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="$REPO_ROOT/custom_data"

echo "Starting upload of $SOURCE_DIR to $BUCKET_PATH"

# Check if gsutil is available
if ! command -v gsutil &> /dev/null; then
    echo "Error: gsutil is not installed or not in PATH"
    echo "Please install Google Cloud SDK and authenticate with 'gcloud auth login'"
    exit 1
fi

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR does not exist"
    exit 1
fi

# Check if user is authenticated
if ! gsutil ls gs://internal-llm-rnd &> /dev/null; then
    echo "Error: Not authenticated with Google Cloud or bucket doesn't exist"
    echo "Please run 'gcloud auth login' and ensure you have access to the bucket"
    exit 1
fi

echo "Uploading contents of $SOURCE_DIR to $BUCKET_PATH (skipping existing files)..."

# Use gsutil with parallel uploads (-m), no-clobber (-n), and recursive copy (-r)
# -n ensures only files that do NOT already exist at the destination are uploaded
# This preserves the directory structure
gsutil -m cp -n -r "$SOURCE_DIR"/* "$BUCKET_PATH/"

if [ $? -eq 0 ]; then
    echo "Upload completed successfully!"
    echo "Contents uploaded to: $BUCKET_PATH"
else
    echo "Error: Upload failed"
    exit 1
fi
