from fastapi import APIRouter, Query, Request

from ..logger import log_request, log_response
from .schema import (
    CreateDocumentRequest,
    DocumentResponse,
    SimilarSearchResponse,
)
from .service import create_document, search_similar_documents

router = APIRouter()


@router.post("", response_model=DocumentResponse)
async def create_document_endpoint(
    req: CreateDocumentRequest, request: Request
) -> DocumentResponse:
    """ドキュメントを embedding 付きで保存する（pgvector サンプル）。"""
    log_request(req, endpoint="POST /documents")
    res = create_document(request.app.state.db, req)
    log_response(res, endpoint="POST /documents")
    return res


@router.get("/similar", response_model=SimilarSearchResponse)
async def search_similar_documents_endpoint(
    request: Request,
    q: str = Query(min_length=1, max_length=500, description="検索クエリ文字列"),
    limit: int = Query(default=5, ge=1, le=50),
) -> SimilarSearchResponse:
    """クエリ文字列に近いドキュメントをコサイン距離で返す（pgvector サンプル）。"""
    res = search_similar_documents(request.app.state.db, query=q, limit=limit)
    log_response(res, endpoint="GET /documents/similar")
    return res
