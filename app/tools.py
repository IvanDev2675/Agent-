import json
import re
from pathlib import Path

REQUEST_ID_RE = re.compile(r"^REQ-\d{3,6}$")

IMPACT_POINTS = {"bajo": 1, "medio": 2, "alto": 3, "critico": 4}
COMPLEXITY_DAYS = {"baja": 2, "media": 5, "alta": 10}


class ToolError(ValueError):
    """Argumentos inválidos enviados por el modelo a una herramienta."""


def get_request_status(request_id: str, requests_path: Path) -> dict:
    if not isinstance(request_id, str) or not REQUEST_ID_RE.match(request_id.strip().upper()):
        raise ToolError("request_id debe tener el formato REQ-1234")
    rid = request_id.strip().upper()
    data = json.loads(Path(requests_path).read_text("utf-8"))
    for item in data:
        if item["id"] == rid:
            return item
    return {"id": rid, "error": "Solicitud no encontrada"}


def classify_priority(impact: str, users_affected: int, has_workaround: bool) -> dict:
    impact = str(impact).strip().lower().replace("í", "i")
    if impact not in IMPACT_POINTS:
        raise ToolError("impact debe ser: bajo, medio, alto o critico")
    if not isinstance(users_affected, int) or isinstance(users_affected, bool) or users_affected < 0:
        raise ToolError("users_affected debe ser un entero >= 0")
    if not isinstance(has_workaround, bool):
        raise ToolError("has_workaround debe ser booleano")

    users_points = 0 if users_affected < 10 else 1 if users_affected < 100 else 2 if users_affected < 500 else 3
    score = IMPACT_POINTS[impact] + users_points + (0 if has_workaround else 2)
    priority = "Crítica" if score >= 8 else "Alta" if score >= 6 else "Media" if score >= 3 else "Baja"
    return {"priority": priority, "score": score, "rules": "impacto + usuarios + (2 si no hay workaround)"}


def estimate_effort(complexity: str, integrations: int, data_migration: bool) -> dict:
    complexity = str(complexity).strip().lower()
    if complexity not in COMPLEXITY_DAYS:
        raise ToolError("complexity debe ser: baja, media o alta")
    if not isinstance(integrations, int) or isinstance(integrations, bool) or not 0 <= integrations <= 50:
        raise ToolError("integrations debe ser un entero entre 0 y 50")
    if not isinstance(data_migration, bool):
        raise ToolError("data_migration debe ser booleano")

    days = COMPLEXITY_DAYS[complexity] + 2 * integrations + (3 if data_migration else 0)
    return {"estimated_days": days, "rules": "base por complejidad + 2 por integración + 3 si migra datos"}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Busca fragmentos en la documentación interna (procedimientos, políticas, guías). "
            "Úsala para cualquier pregunta sobre normas, SLAs, procesos o guías.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Consulta en lenguaje natural"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_request_status",
            "description": "Consulta el estado de una solicitud interna por su ID (formato REQ-1234).",
            "parameters": {
                "type": "object",
                "properties": {"request_id": {"type": "string"}},
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "classify_priority",
            "description": "Clasifica la prioridad de una solicitud con reglas deterministas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "impact": {"type": "string", "enum": ["bajo", "medio", "alto", "critico"]},
                    "users_affected": {"type": "integer"},
                    "has_workaround": {"type": "boolean"},
                },
                "required": ["impact", "users_affected", "has_workaround"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_effort",
            "description": "Estima el esfuerzo en días para una solicitud según reglas simples.",
            "parameters": {
                "type": "object",
                "properties": {
                    "complexity": {"type": "string", "enum": ["baja", "media", "alta"]},
                    "integrations": {"type": "integer"},
                    "data_migration": {"type": "boolean"},
                },
                "required": ["complexity", "integrations", "data_migration"],
            },
        },
    },
]
