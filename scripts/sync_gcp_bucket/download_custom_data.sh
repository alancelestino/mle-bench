#!/bin/bash

# Script to download/sync custom_data from GCS bucket
# Usage examples:
#   ./download_custom_data.sh                      # default: rsync recursive with checksum
#   ./download_custom_data.sh --missing-only       # cp only missing files (-n)
#   ./download_custom_data.sh --mtime              # rsync based on mtime/size (no checksum)
#   ./download_custom_data.sh --delete             # delete local files not in bucket (rsync only)
#   ./download_custom_data.sh --dry-run            # show actions without executing
#   ./download_custom_data.sh --no-parallel        # disable gsutil -m
#   ./download_custom_data.sh --exclude "\.tmp$"   # exclude regex
#   ./download_custom_data.sh --bucket gs://... --dest /path/to/custom_data

set -e  # Exit on any error

BUCKET_PATH="gs://internal-llm-rnd/mle-bench/turing-tasks"
# Resolve repository root even when called from elsewhere
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEST_DIR="$REPO_ROOT/custom_data"

# Defaults for behavior
MODE="rsync"            # rsync | cp-missing
DELETE_EXTRANEOUS=false  # only applies to rsync
USE_CHECKSUM=true        # rsync -c
DRY_RUN=false
PARALLEL=true            # gsutil -m
EXCLUDE_REGEX=""        # passed as -x to rsync

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)
      BUCKET_PATH="$2"; shift 2;;
    --dest)
      DEST_DIR="$2"; shift 2;;
    --missing-only)
      MODE="cp-missing"; shift;;
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
      echo "Usage: $0 [--bucket gs://bucket/prefix] [--dest /path] [--missing-only|--rsync] [--delete] [--checksum|--mtime] [--dry-run] [--no-parallel|--parallel] [--exclude REGEX]";
      exit 0;;
    *)
      echo "Unknown option: $1"; exit 1;;
  esac
done

echo "Starting download from $BUCKET_PATH to $DEST_DIR"

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

# Build gsutil base
GSUTIL_CMD=(gsutil)
if [ "$PARALLEL" = true ]; then
  GSUTIL_CMD+=("-m")
fi

if [ "$MODE" = "rsync" ]; then
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
    echo "[DRY-RUN] gsutil ${GSUTIL_CMD[*]:1} ${RSYNC_ARGS[*]} \"$BUCKET_PATH\" \"$DEST_DIR\""
  else
    "${GSUTIL_CMD[@]}" "${RSYNC_ARGS[@]}" "$BUCKET_PATH" "$DEST_DIR"
  fi
  echo "Sync finished."
else
  # cp-missing: only copy files that don't exist locally
  # Use trailing slash semantics to copy contents into dest
  CP_ARGS=("cp" "-r" "-n")
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] gsutil ${GSUTIL_CMD[*]:1} ${CP_ARGS[*]} \"$BUCKET_PATH/*\" \"$DEST_DIR/\""
  else
    "${GSUTIL_CMD[@]}" "${CP_ARGS[@]}" "$BUCKET_PATH/*" "$DEST_DIR/"
  fi
  echo "Copy (missing-only) finished."
fi
