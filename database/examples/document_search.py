"""pgvector によるドキュメント類似検索の例。

埋め込みモデルはデモ用の疑似ベクトル。
生成したベクトルを `Document.embedding` に保存する。

    cd database
    make db-up
    uv run python examples/document_search.py

`database/.env` の DB_* を使う（`make` 経由でなくても可）。

SQLAlchemy の基本操作（このスクリプトで使うもの）:
- `session.add(obj)`: セッションに INSERT 対象を登録する（この時点では DB には書かれない）
- `session.flush()`: 未送信の変更を DB に送るが、トランザクションはまだ確定しない。
  Identity で採番される `id` を直後に参照したいときに使う
- `session.commit()`: トランザクションを確定し、変更を永続化する
"""

import hashlib
import math
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from schema.models import EMBEDDING_DIM, Document

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _build_url() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "poc")
    user = os.environ.get("DB_USER", "app_user")
    password = os.environ.get("DB_PASSWORD", "app_password")
    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"
    return f"postgresql+psycopg://{auth}@{host}:{port}/{name}"


def demo_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """デモ用の決定的な疑似ベクトル（本番では埋め込みモデルの出力を使う）。"""
    # 同じ文字列なら常に同じベクトルになるよう、ハッシュから決定的に値を作る
    digest = hashlib.sha256(text.encode()).digest()
    values = [(digest[i % len(digest)] / 127.5) - 1.0 for i in range(dim)]
    # コサイン距離で比較するので長さ 1 に正規化しておく
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values]


def add_document(
    session: Session,
    *,
    title: str,
    content: str,
) -> Document:
    document = Document(
        title=title,
        content=content,
        embedding=demo_embedding(f"{title}\n{content}"),  # 本文を意味ベクトルにして保存
    )
    session.add(document)
    # まだ commit せず DB に送る。直後に document.id を読めるようにするため
    session.flush()
    return document


def search_similar_documents(
    session: Session,
    query: str,
    *,
    limit: int = 3,
) -> list[Document]:
    # クエリ文も同じ方法でベクトル化し、保存済みの embedding と距離を比べる
    query_vec = demo_embedding(query)
    stmt = (
        select(Document)
        # コサイン距離が小さい＝意味が近い順に並べる（HNSW インデックスが効く）
        .order_by(Document.embedding.cosine_distance(query_vec))
        .limit(limit)
    )
    return list(session.scalars(stmt))


def main() -> None:
    engine = create_engine(_build_url())

    # psycopg に pgvector の型を教える。これで list[float] と vector を相互変換できる
    with engine.connect() as conn:
        register_vector(conn.connection.driver_connection)

    samples = [
        (
            "FastAPI 入門",
            "FastAPI は Python の Web フレームワーク。型ヒントと OpenAPI を標準サポートする。",
        ),
        (
            "PostgreSQL pgvector",
            "pgvector は PostgreSQL 向けのベクトル型拡張。コサイン距離で類似検索できる。",
        ),
        (
            "Cloud Run デプロイ",
            "Cloud Run はコンテナをサーバーレスで実行する GCP サービス。",
        ),
    ]

    with Session(engine) as session:
        saved: list[Document] = []
        for title, content in samples:
            doc = add_document(session, title=title, content=content)
            # flush 済みなので commit 前でも id が読める（ログ出力などに使える）
            print(f"  add + flush → id={doc.id} title={doc.title!r}")
            saved.append(doc)

        # ここまでの全ドキュメントを 1 トランザクションとして確定する
        session.commit()
        print(f"\n{len(saved)} 件のドキュメントを commit して保存")

        # 保存したドキュメントのどれと意味的に近いかをベクトル検索で確かめる
        query = "ベクトル検索のやり方"
        hits = search_similar_documents(session, query)
        print(f"\nクエリ: {query!r}")
        print("類似度の高いドキュメント:")
        for doc in hits:
            print(f"  [id={doc.id}] {doc.title}: {doc.content}")


if __name__ == "__main__":
    main()
