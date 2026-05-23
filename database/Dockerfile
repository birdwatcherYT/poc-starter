FROM postgres:16

ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8
ENV TZ=Asia/Tokyo

# 必要な PostgreSQL 拡張をここに追加する。
# - pgvector: ベクトル検索（Alembic revision の CREATE EXTENSION vector で有効化）
# 他に postgresql-16-postgis-3 などを追加したい場合は同じ行に並べる。
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        locales \
        postgresql-16-pgvector \
    && sed -i 's/^# \(ja_JP.UTF-8\)/\1/' /etc/locale.gen \
    && locale-gen \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
