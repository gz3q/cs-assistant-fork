import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import func, update

from src.config.logger import get_logger
from src.infrastructure.db import async_session_factory
from src.infrastructure.db.models import SourceRow
from src.infrastructure.db.repository import Repository
from src.ingestion.scrapers.html_scraper import scrape
from src.retrieval.services import embedding_service

log = get_logger(__name__)

# chunk_size is measured in CHARACTERS (default length function is len).
# ~1500 chars ≈ ~375 tokens, in the industry-standard 256-512 token range for RAG.
# Tune via evals once a golden dataset exists.
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def ingest_url(url: str) -> None:
    """Scrape, chunk, embed, and upsert a single URL.

    Idempotent: re-running on unchanged content is a no-op via content_hash conflict.
    """
    log.info("ingest_started", url=url)

    try:
        text, title = scrape(url)
    except Exception as e:
        log.error("scrape_failed", url=url, error=str(e))
        raise

    if not text.strip():
        log.warning("scrape_empty", url=url)
        return

    chunks = _splitter.split_text(text)
    log.info("chunked", url=url, n_chunks=len(chunks))

    async with async_session_factory() as session:
        source = await Repository.get_or_create_source(
            session,
            name=title or url,
            url=url,
            source_type="html",
        )

        for i, chunk_text in enumerate(chunks):
            cleaned = chunk_text.strip()
            if not cleaned:
                continue
            try:
                embedding = await embedding_service.embed_document(cleaned)
            except Exception as e:
                log.error("embed_failed", url=url, chunk_index=i, error=str(e))
                raise

            await Repository.upsert_chunk(
                session,
                content=cleaned,
                embedding=embedding,
                source_url=url,
                source_type="html",
                section_heading=None,
                content_hash=_hash(cleaned),
                source_id=source.id,
            )

        await session.execute(
            update(SourceRow).where(SourceRow.id == source.id).values(last_synced_at=func.now())
        )
        await session.commit()

    log.info("ingest_complete", url=url, n_chunks=len(chunks))
