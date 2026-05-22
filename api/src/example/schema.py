from datetime import datetime

from pydantic import BaseModel, Field


class EchoRequest(BaseModel):
    """`POST /example/echo` のリクエストボディ。"""

    message: str = Field(
        min_length=1,
        max_length=500,
        description="保存したいメッセージ本文",
        examples=["hello"],
    )
    author: str | None = Field(
        default=None,
        max_length=100,
        description="任意の送信者名",
        examples=["alice"],
    )


class EchoResponse(BaseModel):
    """`POST /example/echo` のレスポンス。保存した行をそのまま返す。"""

    id: int = Field(description="DB が払い出した主キー")
    message: str = Field(description="保存されたメッセージ")
    author: str | None = Field(description="送信者名（未指定なら null）")
    created_at: datetime = Field(description="DB が記録した作成時刻")
