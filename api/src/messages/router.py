from fastapi import APIRouter, Query, Request

from ..logger import log_request, log_response
from .schema import CreateMessageRequest, MessageListResponse, MessageResponse
from .service import create_message, list_messages

router = APIRouter()


@router.post("", response_model=MessageResponse)
async def create_message_endpoint(
    req: CreateMessageRequest, request: Request
) -> MessageResponse:
    """メッセージを保存して、保存された行を返す。"""
    log_request(req, endpoint="POST /messages")
    res = create_message(request.app.state.db, req)
    log_response(res, endpoint="POST /messages")
    return res


@router.get("", response_model=MessageListResponse)
async def list_messages_endpoint(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> MessageListResponse:
    """保存されているメッセージを新しい順に返す。"""
    res = list_messages(request.app.state.db, limit=limit)
    log_response(res, endpoint="GET /messages")
    return res
