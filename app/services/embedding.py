import asyncio
from typing import Optional
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model: Optional[SentenceTransformer] = None
        self._model_name = model_name
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def load(self) -> None:
        self._model = SentenceTransformer(self._model_name)

    def is_ready(self) -> bool:
        return self._model is not None

    async def embed(self, text: str) -> list[float]:
        if not self._model:
            raise RuntimeError("Embedding model not loaded")
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(None, lambda: self._model.encode(text).tolist())
        return vector


embedding_service = EmbeddingService()
