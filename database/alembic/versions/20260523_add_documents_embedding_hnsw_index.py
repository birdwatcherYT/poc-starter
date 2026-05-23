"""add documents embedding hnsw index

Revision ID: b7e4c9a21d03
Revises: 201d82f9dea1
Create Date: 2026-05-23 12:00:01

"""

from alembic import op

revision: str = "b7e4c9a21d03"
down_revision: str | None = "201d82f9dea1"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # cosine_distance (<=>) と演算子クラスを合わせる。autogenerate では検出されない。
    op.execute(
        """
        CREATE INDEX documents_embedding_hnsw_idx
          ON documents USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS documents_embedding_hnsw_idx")
