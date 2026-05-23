from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateDocumentRequest(BaseModel):
    """`POST /documents` のリクエストボディ。"""

    title: str = Field(
        min_length=1,
        max_length=200,
        description="ドキュメントのタイトル",
        examples=["猫の生態"],
    )
    content: str = Field(
        min_length=1,
        max_length=5000,
        description="本文。これとタイトルを連結したものから埋め込みを作る（今はダミー）",
        examples=["猫は哺乳類で、夜行性の傾向がある。"],
    )


class DocumentResponse(BaseModel):
    """ドキュメント 1 件分のレスポンス。embedding はレスポンスから除外する（重いため）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="DB が払い出した主キー")
    title: str = Field(description="タイトル")
    content: str = Field(description="本文")
    created_at: datetime = Field(description="DB が記録した作成時刻")


class SimilarDocument(BaseModel):
    """類似検索結果 1 件分。距離（コサイン距離）が小さいほど類似。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="DB が払い出した主キー")
    title: str = Field(description="タイトル")
    content: str = Field(description="本文")
    distance: float = Field(description="クエリとのコサイン距離（0=同一、2=逆向き）")


class SimilarSearchResponse(BaseModel):
    """`GET /documents/similar` のレスポンス。"""

    query: str = Field(description="検索クエリ（埋め込み化して比較した文字列）")
    items: list[SimilarDocument] = Field(description="距離が小さい順の検索結果")
