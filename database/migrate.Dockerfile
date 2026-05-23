# ===== Build Stage =====
FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

# 依存解決に必要なファイルだけ先にコピーして cache を効かせる。
# パッケージ本体（schema/）はビルド時に必要なのでこちらも入れる。
COPY pyproject.toml uv.lock ./
COPY schema schema

RUN uv sync --frozen --no-dev

# ===== Runtime Stage =====
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Alembic 設定とマイグレーション本体
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY schema ./schema

# DB_URL は Cloud Run Job 側の環境変数で渡される想定。
# パスワードを URL に含めない場合は PGPASSWORD も別途渡す（libpq が解決する）。
ENTRYPOINT ["alembic", "upgrade", "head"]
