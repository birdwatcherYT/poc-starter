"""enable pgvector

Revision ID: 2a09a89c5c4b
Revises:
Create Date: 2026-05-22 12:00:01

"""

from alembic import op

revision: str = "2a09a89c5c4b"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
