#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${STRIX_VIEWER_USERNAME:-}" || -z "${STRIX_VIEWER_PASSWORD:-}" ]]; then
    echo "ERROR: Set STRIX_VIEWER_USERNAME and STRIX_VIEWER_PASSWORD for public deployment." >&2
    exit 1
fi
if (( ${#STRIX_VIEWER_PASSWORD} < 20 )); then
    echo "ERROR: STRIX_VIEWER_PASSWORD must contain at least 20 characters." >&2
    exit 1
fi
if [[ -n "${STRIX_WORKER_TOKEN:-}" ]] && (( ${#STRIX_WORKER_TOKEN} < 32 )); then
    echo "ERROR: STRIX_WORKER_TOKEN must contain at least 32 characters." >&2
    exit 1
fi

if [[ ! -d /data ]]; then
    echo "ERROR: Render persistent disk is not mounted at /data." >&2
    exit 1
fi

mkdir -p /data/strix_runs
if [[ -e /app/strix_runs || -L /app/strix_runs ]]; then
    if [[ ! -L /app/strix_runs || "$(readlink -f /app/strix_runs)" != "/data/strix_runs" ]]; then
        echo "ERROR: Refusing to replace unexpected /app/strix_runs path." >&2
        exit 1
    fi
else
    ln -s /data/strix_runs /app/strix_runs
fi

PORT="${PORT:-10000}"
HOST="0.0.0.0"

echo "Starting Strix Viewer on ${HOST}:${PORT}; scan execution is delegated to an external worker."
cd /app
exec strix view --empty --host "${HOST}" --port "${PORT}" --no-open
