from .chunking import chunk_text
from .config import Settings
from .vectorstore import Chunk, Hit


class RagService:
    def __init__(self, store, llm, settings: Settings):
        self.store = store
        self.llm = llm
        self.settings = settings

    def ingest(self, source: str, text: str) -> int:
        pieces = chunk_text(text, self.settings.chunk_size, self.settings.chunk_overlap)
        if not pieces:
            raise ValueError("El documento no contiene texto")
        embeddings = self.llm.embed(pieces)
        self.store.upsert([Chunk(source, i, t, e) for i, (t, e) in enumerate(zip(pieces, embeddings))])
        return len(pieces)

    def retrieve(self, query: str, k: int | None = None) -> list[Hit]:
        vec = self.llm.embed([query])[0]
        return self.store.search(query, vec, k or self.settings.top_k)

    def list_documents(self) -> list[dict]:
        return self.store.list_sources()
