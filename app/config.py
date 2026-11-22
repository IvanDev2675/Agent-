import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    # "azure_search" en la nube; "local" para desarrollo y pruebas sin Azure Search
    vector_backend: str = os.getenv("VECTOR_BACKEND", "azure_search")

    aoai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    aoai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")  # vacío => Entra ID / managed identity
    aoai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    chat_deployment: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
    embedding_deployment: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    embedding_dims: int = _int("EMBEDDING_DIMENSIONS", 1536)

    search_endpoint: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    search_api_key: str = os.getenv("AZURE_SEARCH_API_KEY", "")  # vacío => Entra ID / managed identity
    search_index: str = os.getenv("AZURE_SEARCH_INDEX", "solicitudes-docs")

    service_api_key: str = os.getenv("API_KEY", "")  # si se define, exige X-API-Key
    db_path: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "history.db")))
    local_store_path: Path = Path(os.getenv("LOCAL_STORE_PATH", str(BASE_DIR / "data" / "local_store.json")))
    requests_path: Path = Path(os.getenv("REQUESTS_PATH", str(BASE_DIR / "data" / "requests.json")))

    chunk_size: int = _int("CHUNK_SIZE", 800)
    chunk_overlap: int = _int("CHUNK_OVERLAP", 120)
    top_k: int = _int("TOP_K", 4)
    max_upload_bytes: int = _int("MAX_UPLOAD_BYTES", 1_000_000)
    max_question_chars: int = _int("MAX_QUESTION_CHARS", 2000)
    max_agent_steps: int = _int("MAX_AGENT_STEPS", 5)


@lru_cache
def get_settings() -> Settings:
    return Settings()
