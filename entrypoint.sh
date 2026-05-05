#!/bin/bash
set -e

BUCKET_NAME="${GCS_BUCKET:-new-tracker-expenses}"
MOUNT_DIR="/app/data"

echo "Mounting GCS bucket: $BUCKET_NAME -> $MOUNT_DIR"

gcsfuse \
  --implicit-dirs \
  --file-mode=0666 \
  --dir-mode=0777 \
  --only-dir=data \
  "$BUCKET_NAME" "$MOUNT_DIR"

echo "GCS bucket mounted successfully"

exec streamlit run app.py
