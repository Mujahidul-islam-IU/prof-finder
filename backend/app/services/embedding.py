"""
ProfFinder — OpenAI Embedding Service
Handles text embedding via text-embedding-3-small (1536 dimensions).
"""

from openai import AsyncOpenAI
from app.config import get_settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns 1536-dim vector."""
    settings = get_settings()
    client = _get_client()
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text,
        dimensions=settings.embedding_dimensions,
    )
    return response.data[0].embedding


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single batch API call. Returns list of vectors."""
    if not texts:
        return []
    settings = get_settings()
    client = _get_client()
    # OpenAI batch limit is 2048 inputs; split if needed
    all_embeddings = []
    batch_size = 512
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
            dimensions=settings.embedding_dimensions,
        )
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings
