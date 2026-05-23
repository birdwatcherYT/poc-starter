# ===== Build Stage =====
FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy

WORKDIR /app/api

RUN pip install --no-cache-dir uv

COPY api/pyproject.toml api/uv.lock ./
COPY database/pyproject.toml database/uv.lock /app/database/

# schema の .py は runtime で載せる。ここでは path 依存のメタデータだけで sync する
RUN uv sync --frozen --no-dev

# ===== Runtime Stage =====
FROM python:3.12-slim AS runtime

ENV TZ=Asia/Tokyo \
    LANG=ja_JP.UTF-8 \
    LANGUAGE=ja_JP:ja \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y --no-install-recommends tzdata locales ca-certificates \
    && locale-gen ja_JP.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# builder と同じパスに venv を置く（/app/api/.venv へ移すと console_scripts の shebang が壊れる）
WORKDIR /app/api

COPY --from=builder /app/api/.venv ./.venv
ENV PATH="/app/api/.venv/bin:$PATH" \
    PYTHONPATH="/app/database"

# アプリ本体 + ORM モデル（base.py / __init__.py も import に必要）
COPY api/src src
COPY api/static static
COPY api/api.py api.py
COPY database/schema /app/database/schema

# Cloud Run は PORT を自動で渡してくる。
# WORKERS は CPU 数に応じて調整（Cloud Run は通常 1 CPU なので 1〜2 が無難）。
# max-requests / jitter は worker のメモリリーク対策（一定リクエストごとに再起動）。
ENV PORT=8080 \
    GUNICORN_WORKERS=2 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_MAX_REQUESTS=1000 \
    GUNICORN_MAX_REQUESTS_JITTER=100 \
    LOG_LEVEL=info

EXPOSE 8080

CMD ["sh", "-c", "exec gunicorn \
     -b :${PORT} \
     --workers ${GUNICORN_WORKERS} \
     --worker-class uvicorn.workers.UvicornWorker \
     --timeout ${GUNICORN_TIMEOUT} \
     --max-requests ${GUNICORN_MAX_REQUESTS} \
     --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER} \
     --log-level ${LOG_LEVEL} \
     --access-logfile - \
     --error-logfile - \
     api:app"]
