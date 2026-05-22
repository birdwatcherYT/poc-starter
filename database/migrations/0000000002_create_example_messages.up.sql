CREATE TABLE IF NOT EXISTS example_messages (
    id         BIGSERIAL PRIMARY KEY,
    message    TEXT      NOT NULL,
    author     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
