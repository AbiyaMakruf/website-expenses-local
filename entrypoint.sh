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

# Start Streamlit di background dulu
streamlit run app.py &
STREAMLIT_PID=$!

# Tunggu sampai Streamlit benar-benar siap menerima request
echo "Waiting for Streamlit to be ready..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8080/_stcore/health > /dev/null 2>&1; then
    echo "Streamlit is ready (attempt $i)"
    break
  fi
  echo "Attempt $i: not ready yet, waiting..."
  sleep 2
done

# Serahkan proses ke Streamlit (Cloud Run monitor PID ini)
wait $STREAMLIT_PID
