from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateMessageRequest(BaseModel):
    """`POST /messages` のリクエストボディ。"""

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


class MessageResponse(BaseModel):
    """メッセージ 1 件分のレスポンス。

    `from_attributes=True` により SQLAlchemy の `Message` インスタンスから直接 `MessageResponse.model_validate(orm_obj)` で構築できる。属性名と型が一致していることがランタイムでチェックされる。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="DB が払い出した主キー")
    message: str = Field(description="保存されたメッセージ")
    author: str | None = Field(description="送信者名（未指定なら null）")
    created_at: datetime = Field(description="DB が記録した作成時刻")


class MessageListResponse(BaseModel):
    """`GET /messages` のレスポンス。"""

    items: list[MessageResponse] = Field(description="保存されているメッセージの配列")
    total: int = Field(description="返した件数")
