from ..database import Database
from .schema import EchoRequest, EchoResponse


def echo(db: Database, req: EchoRequest) -> EchoResponse:
    """メッセージを `example_messages` テーブルに insert して返す。"""
    rows = db.fetch(
        """
        INSERT INTO example_messages (message, author)
        VALUES (%(message)s, %(author)s)
        RETURNING id, message, author, created_at
        """,
        {"message": req.message, "author": req.author},
    )
    return EchoResponse(**rows[0])
