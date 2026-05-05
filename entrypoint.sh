#!/bin/bash
set -e

BUCKET_NAME="${GCS_BUCKET:-new-tracker-expenses}"
MOUNT_DIR="/app/data"

echo "Mounting GCS bucket: $BUCKET_NAME -> $MOUNT_DIR"

# Mount GCS bucket ke /app/data
gcsfuse \
  --implicit-dirs \
  --file-mode=0666 \
  --dir-mode=0777 \
  --only-dir=data \
  "$BUCKET_NAME" "$MOUNT_DIR"

echo "GCS bucket mounted successfully"

# Jalankan Streamlit
exec streamlit run app.py \
  --server.port=8080 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --browser.gatherUsageStats=false
