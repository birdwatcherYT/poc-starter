"""documents テーブル。pgvector を使ったベクトル検索のサンプル。

`embedding` は埋め込みベクトル。サンプルとして 384 次元にしてある（軽量な多言語モデル paraphrase-multilingual-MiniLM-L12-v2 などを想定）。実際の埋め込みモデルに合わせて次元数は調整する。

近傍検索は ORM 式で書ける:

    from sqlalchemy import select
    from schema.models import Document

    stmt = (
        select(Document)
        .order_by(Document.embedding.cosine_distance(query_vec))
        .limit(10)
    )
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Identity, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from ..base import Base

EMBEDDING_DIM = 384


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=False
    )
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
