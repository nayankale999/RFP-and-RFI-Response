import logging

import voyageai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.shared.exceptions import AIClientError

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Voyage AI embedding client for vector search."""

    def __init__(self):
        settings = get_settings()
        self.client = voyageai.Client(api_key=settings.voyage_api_key)
        self.model = settings.voyage_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        try:
            result = self.client.embed([text], model=self.model, input_type="document")
            return result.embeddings[0]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise AIClientError(f"Embedding failed: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batched)."""
        try:
            # Voyage AI supports batch embedding, max ~128 texts per call
            all_embeddings = []
            batch_size = 64
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                result = self.client.embed(batch, model=self.model, input_type="document")
                all_embeddings.extend(result.embeddings)
            return all_embeddings
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise AIClientError(f"Batch embedding failed: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query (uses query input type)."""
        try:
            result = self.client.embed([query], model=self.model, input_type="query")
            return result.embeddings[0]
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            raise AIClientError(f"Query embedding failed: {e}")


_embedding_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client
