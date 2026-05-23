"""documents 機能のサービス層（pgvector + SQLAlchemy ORM）。"""

import random

from schema.models import Document
from schema.models.document import EMBEDDING_DIM
from sqlalchemy import select

from ..database import Database
from .schema import (
    CreateDocumentRequest,
    DocumentResponse,
    SimilarDocument,
    SimilarSearchResponse,
)


def _dummy_embed(text: str) -> list[float]:
    """サンプル用のダミー埋め込み。同じ文字列なら同じベクトルを返す（決定的）。

    本来は SentenceTransformer や OpenAI Embeddings API などを呼ぶところ。差し替えるときはこの関数のシグネチャを保てば呼び出し側は変更不要。
    """
    rng = random.Random(text)
    return [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIM)]


def create_document(db: Database, req: CreateDocumentRequest) -> DocumentResponse:
    """ドキュメントを embedding 付きで保存する。

    本来は本文を sentence-transformer 等で埋め込み化するが、サンプルとしてダミー実装の `_dummy_embed()` を使う。シグネチャは保たれているので、実モデルに差し替えても呼び出し側は不変。
    """
    vec = _dummy_embed(f"{req.title}\n{req.content}")
    with db.session() as s:
        doc = Document(title=req.title, content=req.content, embedding=vec)
        s.add(doc)
        s.flush()
        return DocumentResponse.model_validate(doc)


def search_similar_documents(
    db: Database, query: str, limit: int = 5
) -> SimilarSearchResponse:
    """クエリ文字列に近いドキュメントをコサイン距離で上位 `limit` 件返す。

    `Document.embedding.cosine_distance(...)` は pgvector の SQLAlchemy 統合が提供する演算子で、SQL 上は `<=>` 演算子に展開される。`label()` で距離を別カラムとして取り出し、Python 側に持ってくる。
    """
    query_vec = _dummy_embed(query)
    with db.session() as s:
        distance = Document.embedding.cosine_distance(query_vec).label("distance")
        stmt = select(Document, distance).order_by(distance).limit(limit)
        rows = s.execute(stmt).all()
        items = [
            SimilarDocument(
                id=doc.id,
                title=doc.title,
                content=doc.content,
                distance=float(dist),
            )
            for doc, dist in rows
        ]
        return SimilarSearchResponse(query=query, items=items)
