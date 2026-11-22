import hashlib
import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path

from .config import Settings


@dataclass
class Chunk:
    source: str
    index: int
    text: str
    embedding: list[float]

    @property
    def id(self) -> str:
        return hashlib.sha1(f"{self.source}:{self.index}".encode()).hexdigest()


@dataclass
class Hit:
    source: str
    index: int
    text: str
    score: float


class LocalVectorStore:
    """Almacén en JSON con similitud coseno. Solo para desarrollo y pruebas."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._items: list[dict] = json.loads(self.path.read_text("utf-8")) if self.path.exists() else []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._items), "utf-8")

    def upsert(self, chunks: list[Chunk]) -> None:
        with self._lock:
            sources = {c.source for c in chunks}
            self._items = [i for i in self._items if i["source"] not in sources]
            self._items += [
                {"source": c.source, "index": c.index, "text": c.text, "embedding": c.embedding} for c in chunks
            ]
            self._save()

    def search(self, query_text: str, query_vec: list[float], k: int) -> list[Hit]:
        def cos(a: list[float], b: list[float]) -> float:
            na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
            return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0

        scored = [Hit(i["source"], i["index"], i["text"], cos(query_vec, i["embedding"])) for i in self._items]
        return sorted(scored, key=lambda h: h.score, reverse=True)[:k]

    def list_sources(self) -> list[dict]:
        counts: dict[str, int] = {}
        for i in self._items:
            counts[i["source"]] = counts.get(i["source"], 0) + 1
        return [{"source": s, "chunks": n} for s, n in sorted(counts.items())]


class AzureSearchStore:
    """Azure AI Search con búsqueda híbrida (texto + vector)."""

    def __init__(self, settings: Settings):
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient

        self.settings = settings
        if settings.search_api_key:
            from azure.core.credentials import AzureKeyCredential

            cred = AzureKeyCredential(settings.search_api_key)
        else:
            from azure.identity import DefaultAzureCredential

            cred = DefaultAzureCredential()
        self._index_client = SearchIndexClient(settings.search_endpoint, cred)
        self._client = SearchClient(settings.search_endpoint, settings.search_index, cred)
        self._ensure_index()

    def _ensure_index(self) -> None:
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        index = SearchIndex(
            name=self.settings.search_index,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.settings.embedding_dims,
                    vector_search_profile_name="vec-profile",
                ),
            ],
            vector_search=VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
                profiles=[VectorSearchProfile(name="vec-profile", algorithm_configuration_name="hnsw")],
            ),
        )
        self._index_client.create_or_update_index(index)

    def _delete_source(self, source: str) -> None:
        safe = source.replace("'", "''")
        old = list(self._client.search(search_text="*", filter=f"source eq '{safe}'", select=["id"], top=1000))
        if old:
            self._client.delete_documents([{"id": d["id"]} for d in old])

    def upsert(self, chunks: list[Chunk]) -> None:
        for source in {c.source for c in chunks}:
            self._delete_source(source)
        self._client.upload_documents(
            [
                {
                    "id": c.id,
                    "source": c.source,
                    "chunk_index": c.index,
                    "content": c.text,
                    "embedding": c.embedding,
                }
                for c in chunks
            ]
        )

    def search(self, query_text: str, query_vec: list[float], k: int) -> list[Hit]:
        from azure.search.documents.models import VectorizedQuery

        vq = VectorizedQuery(vector=query_vec, k_nearest_neighbors=k, fields="embedding")
        results = self._client.search(search_text=query_text, vector_queries=[vq], top=k)
        return [Hit(r["source"], r["chunk_index"], r["content"], r["@search.score"]) for r in results]

    def list_sources(self) -> list[dict]:
        results = self._client.search(search_text="*", facets=["source,count:100"], top=0)
        return [{"source": f["value"], "chunks": f["count"]} for f in results.get_facets().get("source", [])]


def build_vector_store(settings: Settings):
    if settings.vector_backend == "local":
        return LocalVectorStore(settings.local_store_path)
    return AzureSearchStore(settings)
