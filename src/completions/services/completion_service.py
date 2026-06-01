from src.completions.prompts import build_messages
from src.config.logger import get_logger
from src.domain.types import Answer, RetrievedChunk, Source
from src.infrastructure import llm
from src.retrieval.services import retrieval_service

log = get_logger(__name__)


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for rc in chunks:
        parts.append(f"[Source: {rc.chunk.source_url}]\n{rc.chunk.content}")
    return "---\n" + "\n\n".join(parts) + "\n---"


def _extract_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    seen: dict[str, Source] = {}
    for rc in chunks:
        url = rc.chunk.source_url
        if url not in seen:
            seen[url] = Source(url=url, title=None)
    return list(seen.values())


async def ask(question: str) -> Answer:
    """Answer a question using retrieved chunks. Returns abstain Answer if nothing matched."""
    log.info("ask_started", question_len=len(question))

    chunks = await retrieval_service.get_relevant_chunks(question)

    if not chunks:
        log.info("ask_abstain", reason="no_chunks")
        return Answer(
            text="I don't have any information about that in my sources.",
            sources=[],
            confidence="abstain",
        )

    context = _format_context(chunks)
    messages = build_messages(question, context)

    try:
        response_text = await llm.chat(messages)
    except Exception as e:
        log.error("llm_call_failed", error=str(e))
        raise

    log.info("ask_complete", n_sources=len(chunks))
    return Answer(
        text=response_text,
        sources=_extract_sources(chunks),
        confidence="high",
    )
