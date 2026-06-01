from src.infrastructure import llm


async def embed_document(text: str) -> list[float]:
    """Embed text that will be stored and retrieved (indexed content)."""
    return await llm.embed(text, is_query=False)


async def embed_query(text: str) -> list[float]:
    """Embed a user's question for retrieval."""
    return await llm.embed(text, is_query=True)
