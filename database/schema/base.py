"""全モデルの基底クラス。

Alembic はこの metadata を見て差分を検出するので、新しいモデルファイルからは必ずこの Base を継承する。複数ファイルで宣言したテーブルが 1 つの metadata に集まる。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
