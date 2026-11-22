import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class HistoryStore:
    """Trazabilidad de interacciones en SQLite (en producción: Cosmos DB o Azure SQL)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    request_id TEXT,
                    session_id TEXT,
                    question TEXT NOT NULL,
                    answer TEXT,
                    sources TEXT,
                    tool_calls TEXT,
                    latency_ms INTEGER,
                    status TEXT NOT NULL,
                    error TEXT
                )"""
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def log(self, *, request_id, session_id, question, answer, sources, tool_calls, latency_ms, status, error=None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO interactions (ts, request_id, session_id, question, answer, sources, tool_calls,"
                " latency_ms, status, error) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    request_id,
                    session_id,
                    question,
                    answer,
                    json.dumps(sources, ensure_ascii=False),
                    json.dumps(tool_calls, ensure_ascii=False),
                    latency_ms,
                    status,
                    error,
                ),
            )
            return cur.lastrowid

    def list(self, limit: int = 50, session_id: str | None = None) -> list[dict]:
        query, params = "SELECT * FROM interactions", []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._conn() as c:
            rows = c.execute(query, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d["sources"] or "[]")
            d["tool_calls"] = json.loads(d["tool_calls"] or "[]")
            out.append(d)
        return out
