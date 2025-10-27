#!/bin/bash

# Script to upload/sync custom_data directory contents to GCS bucket
# Usage examples:
#   ./upload_custom_data.sh                         # default: cp missing-only (no overwrite)
#   ./upload_custom_data.sh --overwrite             # cp and overwrite existing
#   ./upload_custom_data.sh --rsync                 # rsync local->GCS (mirror)
#   ./upload_custom_data.sh --rsync --delete        # delete bucket objs not present locally
#   ./upload_custom_data.sh --dry-run               # show actions without executing
#   ./upload_custom_data.sh --no-parallel           # disable gsutil -m
#   ./upload_custom_data.sh --exclude "\.tmp$"      # exclude regex (rsync only)
#   ./upload_custom_data.sh --bucket gs://... --source /path/to/custom_data

set -e  # Exit on any error

BUCKET_PATH="gs://internal-llm-rnd/mle-bench/turing-tasks"
# Resolve repository root even when called from elsewhere
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="$REPO_ROOT/custom_data"

# Defaults
MODE="cp"                # cp | rsync
OVERWRITE=false          # for cp
DELETE_EXTRANEOUS=false  # for rsync
USE_CHECKSUM=true        # rsync -c
DRY_RUN=false
PARALLEL=true
EXCLUDE_REGEX=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)
      BUCKET_PATH="$2"; shift 2;;
    --source)
      SOURCE_DIR="$2"; shift 2;;
    --overwrite)
      OVERWRITE=true; MODE="cp"; shift;;
    --no-overwrite|--missing-only)
      OVERWRITE=false; MODE="cp"; shift;;
    --rsync)
      MODE="rsync"; shift;;
    --delete)
      DELETE_EXTRANEOUS=true; shift;;
    --checksum|--checksums|--c)
      USE_CHECKSUM=true; shift;;
    --mtime|--no-checksum)
      USE_CHECKSUM=false; shift;;
    --dry-run)
      DRY_RUN=true; shift;;
    --no-parallel)
      PARALLEL=false; shift;;
    --parallel)
      PARALLEL=true; shift;;
    --exclude)
      EXCLUDE_REGEX="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 [--bucket gs://bucket/prefix] [--source /path] [--overwrite|--no-overwrite] [--rsync] [--delete] [--checksum|--mtime] [--dry-run] [--no-parallel|--parallel] [--exclude REGEX]";
      exit 0;;
    *)
      echo "Unknown option: $1"; exit 1;;
  esac
done

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

# Build gsutil base
GSUTIL_CMD=(gsutil)
if [ "$PARALLEL" = true ]; then
  GSUTIL_CMD+=("-m")
fi

if [ "$MODE" = "rsync" ]; then
  echo "Using rsync mode (local -> bucket)"
  RSYNC_ARGS=("rsync" "-r")
  if [ "$USE_CHECKSUM" = true ]; then
    RSYNC_ARGS+=("-c")
  fi
  if [ "$DELETE_EXTRANEOUS" = true ]; then
    RSYNC_ARGS+=("-d")
  fi
  if [ -n "$EXCLUDE_REGEX" ]; then
    RSYNC_ARGS+=("-x" "$EXCLUDE_REGEX")
  fi
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] gsutil ${GSUTIL_CMD[*]:1} ${RSYNC_ARGS[*]} \"$SOURCE_DIR\" \"$BUCKET_PATH\""
  else
    "${GSUTIL_CMD[@]}" "${RSYNC_ARGS[@]}" "$SOURCE_DIR" "$BUCKET_PATH"
  fi
else
  echo "Using cp mode"
  CP_ARGS=("cp" "-r")
  if [ "$OVERWRITE" = false ]; then
    CP_ARGS+=("-n")
  fi
  # Trailing slashes to copy contents of source into bucket prefix
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] gsutil ${GSUTIL_CMD[*]:1} ${CP_ARGS[*]} \"$SOURCE_DIR/*\" \"$BUCKET_PATH/\""
  else
    "${GSUTIL_CMD[@]}" "${CP_ARGS[@]}" "$SOURCE_DIR"/* "$BUCKET_PATH/"
  fi
fi

echo "Upload completed."
