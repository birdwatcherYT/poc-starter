FROM migrate/migrate:v4.17.0

COPY migrations /migrations

# DB_URL は Cloud Run Job 側の環境変数で渡される想定。
ENTRYPOINT ["sh", "-c", "exec migrate -path=/migrations -database=\"$DB_URL\" up"]
