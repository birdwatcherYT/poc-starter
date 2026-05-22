from fastapi import APIRouter, Request

from ..logger import log_request, log_response
from .schema import EchoRequest, EchoResponse
from .service import echo

router = APIRouter()


@router.post("/echo", response_model=EchoResponse)
async def echo_endpoint(req: EchoRequest, request: Request) -> EchoResponse:
    log_request(req, endpoint="/example/echo")
    res = echo(request.app.state.db, req)
    log_response(res, endpoint="/example/echo")
    return res
