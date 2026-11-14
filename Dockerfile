FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY strix ./strix
COPY scripts/tui_sidecar_hook.py ./scripts/tui_sidecar_hook.py

RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:${PATH}"

RUN mkdir -p /data/strix_runs

EXPOSE 10000

COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
