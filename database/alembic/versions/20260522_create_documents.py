"""create documents

Revision ID: 201d82f9dea1
Revises: 8cdea3fe8600
Create Date: 2026-05-22 12:00:03

"""

import pgvector.sqlalchemy
import sqlalchemy as sa

from alembic import op

revision: str = "201d82f9dea1"
down_revision: str | None = "8cdea3fe8600"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(384),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("documents")
