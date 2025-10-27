#!/bin/bash

# Script to download custom_data from GCS bucket (only missing files)
# Usage: ./download_custom_data.sh

set -e  # Exit on any error

BUCKET_PATH="gs://internal-llm-rnd/mle-bench/turing-tasks"
DEST_DIR="./custom_data"

echo "Starting selective download from $BUCKET_PATH to $DEST_DIR"

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

echo "Checking for files to download..."

# Get list of all files in bucket (relative paths)
# This will give us paths like: custom_data/dataset_id_1/file.txt
BUCKET_FILES=$(gsutil ls -r "$BUCKET_PATH/**" 2>/dev/null | grep -v "/$" | sed "s|$BUCKET_PATH/||")

if [ -z "$BUCKET_FILES" ]; then
    echo "No files found in bucket at $BUCKET_PATH"
    exit 0
fi

DOWNLOAD_COUNT=0

# Process each file
echo "$BUCKET_FILES" | while read -r file_path; do
    local_path="$DEST_DIR/${file_path#custom_data/}"  # Remove bucket prefix

    # Check if local file exists
    if [ ! -f "$local_path" ]; then
        echo "Downloading: $file_path -> $local_path"
        # Create directory structure if needed
        mkdir -p "$(dirname "$local_path")"
        # Download the file
        if gsutil cp "$BUCKET_PATH/$file_path" "$local_path" 2>/dev/null; then
            ((DOWNLOAD_COUNT++))
        else
            echo "Warning: Failed to download $file_path"
        fi
    else
        echo "Skipping existing file: $local_path"
    fi
done

echo "Download completed! Downloaded $DOWNLOAD_COUNT new files."
echo "Existing files were preserved (no rewrites)."
