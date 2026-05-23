"""messages 機能のサービス層（SQLAlchemy ORM 使用）。"""

from schema.models import Message
from sqlalchemy import select

from ..database import Database
from .schema import CreateMessageRequest, MessageListResponse, MessageResponse


def create_message(db: Database, req: CreateMessageRequest) -> MessageResponse:
    """メッセージを `messages` に insert し、保存後の行を返す。

    ORM を使うと:
    - `Message(...)` の引数チェックがコンストラクタで効く
    - INSERT 後に `msg.id` / `msg.created_at` が DB から返った値で自動補完される
    - SQL は SQLAlchemy が組むので、テーブル名・列名のタイポをコンパイル時に検知できる
    """
    with db.session() as s:
        msg = Message(message=req.message, author=req.author)
        s.add(msg)
        s.flush()  # INSERT を実行して id / created_at を取得（commit は session() 終了時）
        # ORM インスタンスから pydantic への変換は from_attributes=True で属性名一致を保証。
        return MessageResponse.model_validate(msg)


def list_messages(db: Database, limit: int = 50) -> MessageListResponse:
    """保存されているメッセージを新しい順に返す。

    `select(Message)` を使うと:
    - `Message.created_at` のように列を Python 属性で参照できる
    - 列名を文字列で書かないので、リネーム時にコンパイル/型チェックで気付ける
    """
    with db.session() as s:
        stmt = select(Message).order_by(Message.created_at.desc()).limit(limit)
        rows = s.scalars(stmt).all()
        items = [MessageResponse.model_validate(r) for r in rows]
        return MessageListResponse(items=items, total=len(items))
