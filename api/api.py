import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.database import Database
from src.documents.router import router as documents_router
from src.logger import configure_logging, get_logger
from src.messages.router import router as messages_router
from src.trace_context import install as install_trace_middleware

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_REQUIRED_DB_VARS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER")


def _build_database() -> Database:
    missing = [k for k in _REQUIRED_DB_VARS if not os.getenv(k)]
    if missing:
        raise ValueError(f"必須の DB 環境変数が未設定です: {', '.join(missing)}")
    return Database(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.getenv("DB_PASSWORD", ""),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    app.state.db = _build_database()
    logger.info("startup complete")
    try:
        yield
    finally:
        app.state.db.close()
        logger.info("shutdown complete")


app = FastAPI(
    title="PoC Starter API",
    description="本番運用を見据えた FastAPI + PostgreSQL の PoC スターター。",
    version="0.1.0",
    lifespan=lifespan,
)

install_trace_middleware(app)

app.include_router(messages_router, prefix="/messages", tags=["messages"])
app.include_router(documents_router, prefix="/documents", tags=["documents"])


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """liveness 用。"""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

