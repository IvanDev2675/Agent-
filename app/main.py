import logging
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePath

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .agent import Agent
from .config import Settings, get_settings
from .history import HistoryStore
from .llm import LLMClient
from .logging_config import log_event, setup_logging
from .rag import RagService
from .vectorstore import build_vector_store

setup_logging()
logger = logging.getLogger("app")

ALLOWED_EXTENSIONS = {".txt", ".md"}
SESSION_RE = r"^[A-Za-z0-9_-]{1,64}$"


@dataclass
class Services:
    settings: Settings
    rag: RagService
    agent: Agent
    history: HistoryStore


@lru_cache
def get_services() -> Services:
    settings = get_settings()
    llm = LLMClient(settings)
    rag = RagService(build_vector_store(settings), llm, settings)
    return Services(settings, rag, Agent(llm, rag, settings), HistoryStore(settings.db_path))


def require_api_key(x_api_key: str | None = Header(default=None), services: Services = Depends(get_services)) -> None:
    expected = services.settings.service_api_key
    if expected and not secrets.compare_digest(x_api_key or "", expected):
        raise HTTPException(status_code=401, detail="API key inválida o ausente")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    session_id: str | None = Field(default=None, pattern=SESSION_RE)


class AskResponse(BaseModel):
    interaction_id: int
    answer: str
    sources: list[dict]
    tool_calls: list[dict]
    latency_ms: int


app = FastAPI(title="Asistente RAG de solicitudes internas", version="1.0.0")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("unhandled_error", extra={"extra_fields": {"request_id": getattr(request.state, "request_id", None)}})
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents", dependencies=[Depends(require_api_key)], status_code=201)
async def upload_document(file: UploadFile = File(...), services: Services = Depends(get_services)):
    name = re.sub(r"[^A-Za-z0-9._-]", "_", PurePath(file.filename or "").name)
    if not name or PurePath(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .txt o .md")

    limit = services.settings.max_upload_bytes
    raw = await file.read(limit + 1)
    if len(raw) > limit:
        raise HTTPException(status_code=413, detail=f"El archivo supera {limit} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="El archivo debe estar codificado en UTF-8")

    try:
        chunks = services.rag.ingest(name, text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    log_event(logger, "document_ingested", source=name, chunks=chunks)
    return {"source": name, "chunks": chunks}


@app.get("/documents", dependencies=[Depends(require_api_key)])
def list_documents(services: Services = Depends(get_services)):
    return services.rag.list_documents()


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(require_api_key)])
def ask(body: AskRequest, request: Request, services: Services = Depends(get_services)):
    started = time.perf_counter()
    rid = request.state.request_id
    try:
        result = services.agent.run(body.question.strip())
    except Exception as exc:
        latency = int((time.perf_counter() - started) * 1000)
        logger.exception("ask_failed", extra={"extra_fields": {"request_id": rid}})
        services.history.log(
            request_id=rid, session_id=body.session_id, question=body.question, answer=None,
            sources=[], tool_calls=[], latency_ms=latency, status="error", error=type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="El servicio de AI no está disponible, intenta de nuevo")

    latency = int((time.perf_counter() - started) * 1000)
    interaction_id = services.history.log(
        request_id=rid, session_id=body.session_id, question=body.question, answer=result.answer,
        sources=result.sources, tool_calls=result.tool_calls, latency_ms=latency, status="ok",
    )
    log_event(logger, "ask", request_id=rid, interaction_id=interaction_id, latency_ms=latency,
              tools=[t["name"] for t in result.tool_calls], sources=len(result.sources))
    return AskResponse(
        interaction_id=interaction_id, answer=result.answer, sources=result.sources,
        tool_calls=result.tool_calls, latency_ms=latency,
    )


@app.get("/history", dependencies=[Depends(require_api_key)])
def history(
    limit: int = Query(default=50, ge=1, le=200),
    session_id: str | None = Query(default=None, pattern=SESSION_RE),
    services: Services = Depends(get_services),
):
    return services.history.list(limit, session_id)
