import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.agent import Agent
from app.config import Settings
from app.history import HistoryStore
from app.llm import ChatReply, ToolCall
from app.main import Services, app, get_services
from app.rag import RagService
from app.vectorstore import LocalVectorStore


class FakeLLM:
    """Embeddings deterministas y respuestas de chat guionadas para pruebas sin Azure."""

    def __init__(self):
        self.script: list[ChatReply] = []

    def embed(self, texts):
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            out.append([b / 255 for b in h[:16]])
        return out

    def chat(self, messages, tools=None):
        return self.script.pop(0)


@pytest.fixture
def env(tmp_path):
    (tmp_path / "requests.json").write_text(
        json.dumps([{"id": "REQ-1002", "status": "En desarrollo"}]), "utf-8"
    )
    settings = Settings(
        vector_backend="local",
        db_path=tmp_path / "h.db",
        local_store_path=tmp_path / "store.json",
        requests_path=tmp_path / "requests.json",
        service_api_key="secreto",
        max_upload_bytes=2000,
    )
    llm = FakeLLM()
    rag = RagService(LocalVectorStore(settings.local_store_path), llm, settings)
    services = Services(settings, rag, Agent(llm, rag, settings), HistoryStore(settings.db_path))
    app.dependency_overrides[get_services] = lambda: services
    yield TestClient(app), llm, {"X-API-Key": "secreto"}
    app.dependency_overrides.clear()


def test_requires_api_key(env):
    client, _, _ = env
    assert client.post("/ask", json={"question": "hola mundo"}).status_code == 401


def test_upload_validations(env):
    client, _, h = env
    assert client.post("/documents", files={"file": ("a.exe", b"x", "text/plain")}, headers=h).status_code == 400
    assert client.post("/documents", files={"file": ("a.txt", b"x" * 3000, "text/plain")}, headers=h).status_code == 413
    assert client.post("/documents", files={"file": ("a.txt", b"\xff\xfe", "text/plain")}, headers=h).status_code == 400
    assert client.post("/documents", files={"file": ("../../a.txt", b"   ", "text/plain")}, headers=h).status_code == 422


def test_ask_validation(env):
    client, _, h = env
    assert client.post("/ask", json={"question": "x" * 2001}, headers=h).status_code == 422
    assert client.post("/ask", json={"question": "valida", "session_id": "../x"}, headers=h).status_code == 422


def test_ingest_ask_with_tool_and_history(env):
    client, llm, h = env
    r = client.post("/documents", files={"file": ("p.md", "El SLA alto es 1 día hábil.".encode(), "text/markdown")}, headers=h)
    assert r.status_code == 201 and r.json()["chunks"] == 1

    llm.script = [
        ChatReply(None, [ToolCall("1", "search_documents", json.dumps({"query": "SLA alto"})),
                         ToolCall("2", "get_request_status", json.dumps({"request_id": "REQ-1002"}))]),
        ChatReply("El SLA es 1 día hábil [p.md] y REQ-1002 está En desarrollo."),
    ]
    r = client.post("/ask", json={"question": "SLA y estado", "session_id": "s1"}, headers=h)
    body = r.json()
    assert r.status_code == 200
    assert body["sources"][0]["source"] == "p.md"
    assert [t["name"] for t in body["tool_calls"]] == ["search_documents", "get_request_status"]

    hist = client.get("/history", params={"session_id": "s1"}, headers=h).json()
    assert len(hist) == 1 and hist[0]["status"] == "ok"


def test_invalid_tool_args_are_reported_to_model_not_crash(env):
    client, llm, h = env
    llm.script = [
        ChatReply(None, [ToolCall("1", "get_request_status", json.dumps({"request_id": "'; DROP TABLE"}))]),
        ChatReply("No pude consultar esa solicitud."),
    ]
    r = client.post("/ask", json={"question": "estado raro"}, headers=h)
    assert r.status_code == 200
    assert r.json()["tool_calls"][0]["status"] == "error"


def test_llm_failure_returns_502_and_is_logged(env):
    client, llm, h = env
    llm.script = []  # pop de lista vacía => excepción
    r = client.post("/ask", json={"question": "falla esto"}, headers=h)
    assert r.status_code == 502
    assert client.get("/history", headers=h).json()[0]["status"] == "error"
