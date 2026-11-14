#!/usr/bin/env bash
set -e

# Ensure persistent disk directory exists and is linked properly
if [ -d "/data" ]; then
    mkdir -p /data/strix_runs
    rm -rf /app/strix_runs
    ln -sfn /data/strix_runs /app/strix_runs
    echo "✅ Using Render persistent disk at /data/strix_runs"
else
    mkdir -p /app/strix_runs
    echo "✅ Using local /app/strix_runs"
fi

PORT="${PORT:-10000}"
HOST="0.0.0.0"

echo "Starting Strix Viewer on ${HOST}:${PORT}..."
exec strix view --host "${HOST}" --port "${PORT}" --no-open
