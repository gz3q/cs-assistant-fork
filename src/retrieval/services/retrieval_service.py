from src.config import settings
from src.config.logger import get_logger
from src.domain.types import RetrievedChunk
from src.infrastructure.db import async_session_factory
from src.infrastructure.db.repository import Repository
from src.retrieval.services import embedding_service

log = get_logger(__name__)


async def get_relevant_chunks(question: str) -> list[RetrievedChunk]:
    """Embed the question and return the top-k most similar chunks."""
    log.info("retrieval_started", question_len=len(question))
    query_embedding = await embedding_service.embed_query(question)

    async with async_session_factory() as session:
        results = await Repository.top_k_chunks(session, query_embedding, k=settings.top_k)

    log.info("retrieval_complete", n_chunks=len(results))
    return results
