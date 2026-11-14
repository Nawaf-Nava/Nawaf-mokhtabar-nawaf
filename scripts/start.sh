#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${STRIX_WORKER_TOKEN:-}" ]] && (( ${#STRIX_WORKER_TOKEN} < 32 )); then
    echo "ERROR: STRIX_WORKER_TOKEN must contain at least 32 characters." >&2
    exit 1
fi

# Render Free has no persistent disk. Keep results on the container's
# writable ephemeral filesystem; they survive only until the instance is
# replaced, restarted, or redeployed.
RUNS_DIR="${STRIX_RUNS_DIR:-/tmp/strix_runs}"
mkdir -p "$RUNS_DIR"

if [[ -e /app/strix_runs || -L /app/strix_runs ]]; then
    if [[ ! -L /app/strix_runs || "$(readlink -f /app/strix_runs)" != "$(readlink -f "$RUNS_DIR")" ]]; then
        echo "ERROR: Refusing to replace unexpected /app/strix_runs path." >&2
        exit 1
    fi
else
    ln -s "$RUNS_DIR" /app/strix_runs
fi

PORT="${PORT:-10000}"
HOST="0.0.0.0"

echo "Starting Strix Viewer on ${HOST}:${PORT}; results use ephemeral storage at ${RUNS_DIR}; scan execution is delegated to an external worker."
cd /app
exec strix view --empty --host "$HOST" --port "$PORT" --no-open
