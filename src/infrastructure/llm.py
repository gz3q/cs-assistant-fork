import httpx

from src.config import settings
from src.config.logger import get_logger

log = get_logger(__name__)

# nomic-embed-text recommends task-specific prefixes for best retrieval quality.
# See https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
EMBED_DOCUMENT_PREFIX = "search_document: "
EMBED_QUERY_PREFIX = "search_query: "


async def embed(text: str, *, is_query: bool = False) -> list[float]:
    """Generate an embedding for a single piece of text.

    is_query=False for content being indexed, is_query=True for search queries.
    The prefix is a nomic-embed-text specific optimization; harmless for other models.
    """
    prefix = EMBED_QUERY_PREFIX if is_query else EMBED_DOCUMENT_PREFIX
    payload = {"model": settings.ollama_embedding_model, "prompt": prefix + text}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{settings.ollama_url}/api/embeddings", json=payload)
        response.raise_for_status()
    data = response.json()
    embedding = data["embedding"]
    if len(embedding) != settings.embedding_dim:
        raise ValueError(
            f"Embedding dim mismatch: model returned {len(embedding)}, "
            f"settings.embedding_dim={settings.embedding_dim}. "
            f"Update EMBEDDING_DIM in .env to match the model."
        )
    return embedding


async def chat(messages: list[dict[str, str]]) -> str:
    """Send a chat completion request and return the response text.

    messages: list of {"role": "system" | "user" | "assistant", "content": str}
    """
    payload = {
        "model": settings.ollama_chat_model,
        "messages": messages,
        "stream": False,
    }
    log.info("ollama_chat_request", model=settings.ollama_chat_model, n_messages=len(messages))
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
        response.raise_for_status()
    data = response.json()
    return data["message"]["content"]
