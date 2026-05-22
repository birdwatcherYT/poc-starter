"""src/database.py の振る舞いを担保する integration test。

特に重要なのは `pool.connection()` の context manager が以下を満たすこと:
- 正常終了で commit する
- 例外発生で rollback する
- `transaction()` でラップした複数文がアトミックに扱われる

これは psycopg3 公式が保証している挙動だが、誰かが将来コードを書き換えたとき気付けるようにテストで縛っておく。
"""

import psycopg
import pytest

from src.database import Database


def _count(db: Database) -> int:
    return db.fetch("SELECT COUNT(*) AS c FROM example_messages")[0]["c"]


def test_get_connection_commits_on_success(
    db: Database, clean_example_messages: None
) -> None:
    """ブロックが正常終了したら自動 commit される。"""
    with db.get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO example_messages (message) VALUES ('committed')",
        )
    assert _count(db) == 1


def test_get_connection_rolls_back_on_exception(
    db: Database, clean_example_messages: None
) -> None:
    """ブロック内で例外が起きたら INSERT は rollback される。"""

    class _Boom(Exception):
        pass

    with pytest.raises(_Boom):
        with db.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO example_messages (message) VALUES ('should-rollback')"
            )
            raise _Boom

    assert _count(db) == 0, "例外時に INSERT が rollback されず、行が残っている"


def test_get_connection_rolls_back_on_sql_error(
    db: Database, clean_example_messages: None
) -> None:
    """ブロックの途中で SQL エラーが出ても、それ以前の INSERT は rollback される。"""
    with pytest.raises(psycopg.errors.UndefinedColumn):
        with db.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO example_messages (message) VALUES ('partial-fail')"
            )
            cur.execute("SELECT no_such_column FROM example_messages")

    assert _count(db) == 0


def test_transaction_groups_multiple_statements_atomically(
    db: Database, clean_example_messages: None
) -> None:
    """`db.transaction()` 内で複数 INSERT を実行し、後で失敗すると全部巻き戻る。"""
    with pytest.raises(psycopg.errors.UndefinedColumn):
        with db.transaction() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO example_messages (message) VALUES ('a')")
            cur.execute("INSERT INTO example_messages (message) VALUES ('b')")
            cur.execute("SELECT no_such_column FROM example_messages")

    assert _count(db) == 0


def test_transaction_commits_when_block_completes(
    db: Database, clean_example_messages: None
) -> None:
    """`db.transaction()` ブロックが正常終了すれば commit される。"""
    with db.transaction() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO example_messages (message) VALUES ('a')")
        cur.execute("INSERT INTO example_messages (message) VALUES ('b')")

    assert _count(db) == 2


def test_execute_returns_rowcount(db: Database, clean_example_messages: None) -> None:
    """execute() は影響行数（rowcount）を返す。"""
    inserted = db.execute(
        "INSERT INTO example_messages (message) VALUES ('x'), ('y'), ('z')"
    )
    assert inserted == 3

    updated = db.execute(
        "UPDATE example_messages SET author = %(a)s",
        {"a": "all"},
    )
    assert updated == 3

    deleted = db.execute("DELETE FROM example_messages")
    assert deleted == 3


def test_fetch_returns_dict_rows(db: Database, clean_example_messages: None) -> None:
    """fetch() は dict_row なので key で値を取れる。"""
    db.execute("INSERT INTO example_messages (message, author) VALUES ('hi', 'me')")
    rows = db.fetch(
        "SELECT message, author FROM example_messages WHERE message = %(m)s",
        {"m": "hi"},
    )
    assert isinstance(rows[0], dict)
    assert rows[0]["message"] == "hi"
    assert rows[0]["author"] == "me"
