# ===== Build Stage =====
FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

# 依存ファイルのみコピーして cache レイヤーを効かせる
COPY pyproject.toml uv.lock ./

# 本番用依存のみインストール（dev グループは入れない）
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

WORKDIR /app

# builder で作った venv をそのままコピー
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# アプリ本体
COPY src src
COPY static static
COPY api.py api.py

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
