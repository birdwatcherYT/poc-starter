"""create messages

Revision ID: 8cdea3fe8600
Revises: 2a09a89c5c4b
Create Date: 2026-05-22 12:00:02

"""

import sqlalchemy as sa

from alembic import op

revision: str = "8cdea3fe8600"
down_revision: str | None = "2a09a89c5c4b"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("messages")
