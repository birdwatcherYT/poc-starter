"""src/database.py の振る舞いを担保する integration test。

`Database.session()` の context manager が以下を満たすことを確認する:
- 正常終了で commit する
- 例外発生で rollback する
- SQL エラーでも rollback する
- 生 SQL（text(...)）と ORM の両方で動く

誰かが将来コードを書き換えたとき気付けるようにテストで縛っておく。
"""

import pytest
from schema.models import Message
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError

from src.database import Database


def _count(db: Database) -> int:
    with db.session() as s:
        return s.scalar(text("SELECT COUNT(*) FROM messages")) or 0


def test_session_commits_on_success(db: Database, clean_messages: None) -> None:
    """ブロックが正常終了したら自動 commit される。"""
    with db.session() as s:
        s.add(Message(message="committed"))
    assert _count(db) == 1


def test_session_rolls_back_on_exception(db: Database, clean_messages: None) -> None:
    """ブロック内で例外が起きたら INSERT は rollback される。"""

    class _Boom(Exception):
        pass

    with pytest.raises(_Boom):
        with db.session() as s:
            s.add(Message(message="should-rollback"))
            s.flush()
            raise _Boom

    assert _count(db) == 0, "例外時に INSERT が rollback されず、行が残っている"


def test_session_rolls_back_on_sql_error(db: Database, clean_messages: None) -> None:
    """SQL エラーでも、それ以前の INSERT は rollback される。"""
    with pytest.raises(ProgrammingError):
        with db.session() as s:
            s.add(Message(message="partial-fail"))
            s.flush()
            s.execute(text("SELECT no_such_column FROM messages"))

    assert _count(db) == 0


def test_session_groups_multiple_inserts_atomically(
    db: Database, clean_messages: None
) -> None:
    """同じ session 内の複数 INSERT は1トランザクションとして扱われ、後で失敗すると全部巻き戻る。"""
    with pytest.raises(ProgrammingError):
        with db.session() as s:
            s.add(Message(message="a"))
            s.add(Message(message="b"))
            s.flush()
            s.execute(text("SELECT no_such_column FROM messages"))

    assert _count(db) == 0


def test_orm_query_returns_typed_instances(db: Database, clean_messages: None) -> None:
    """ORM クエリは Message インスタンスを返し、属性で値にアクセスできる。"""
    with db.session() as s:
        s.add(Message(message="hi", author="me"))

    with db.session() as s:
        row = s.scalars(select(Message)).one()
        assert isinstance(row, Message)
        assert row.message == "hi"
        assert row.author == "me"
        assert isinstance(row.id, int)
        assert row.created_at is not None


def test_raw_sql_with_named_params(db: Database, clean_messages: None) -> None:
    """text() で生 SQL を叩き、:name 形式で bind パラメータを渡せる。"""
    with db.session() as s:
        s.add(Message(message="hi", author="me"))

    with db.session() as s:
        rows = (
            s.execute(
                text("SELECT message, author FROM messages WHERE message = :m"),
                {"m": "hi"},
            )
            .mappings()
            .all()
        )
    assert rows[0]["message"] == "hi"
    assert rows[0]["author"] == "me"
