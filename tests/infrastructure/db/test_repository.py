import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.infrastructure.db.models import ChunkRow
from src.infrastructure.db.repository import Repository


async def test_upsert_and_query(session: AsyncSession):
    """A chunk can be inserted and retrieved via vector similarity.

    Score should be ≈ 1.0 for identical embeddings.
    """
    source = await Repository.get_or_create_source(
        session, name="Test Source", url="https://example.com/test", source_type="html"
    )

    embedding = [0.1] * settings.embedding_dim
    await Repository.upsert_chunk(
        session,
        content="Test content about Carleton CS",
        embedding=embedding,
        source_url="https://example.com/test",
        source_type="html",
        section_heading="Overview",
        content_hash="hash_query_test_001",
        source_id=source.id,
    )

    results = await Repository.top_k_chunks(session, embedding, k=1)

    assert len(results) == 1
    assert results[0].chunk.content == "Test content about Carleton CS"
    assert results[0].chunk.section_heading == "Overview"
    assert results[0].score == pytest.approx(
        1.0, abs=1e-5
    ), "Identical embeddings should produce score ≈ 1.0"


async def test_top_k_ordering(session: AsyncSession):
    """Closer embeddings rank higher than farther ones, with scores descending."""
    source = await Repository.get_or_create_source(
        session, name="Ordering Test", url="https://example.com/ordering", source_type="html"
    )

    near_embedding = [1.0] + [0.0] * (settings.embedding_dim - 1)
    far_embedding = [0.0] * (settings.embedding_dim - 1) + [1.0]

    await Repository.upsert_chunk(
        session,
        content="near match",
        embedding=near_embedding,
        source_url="https://example.com/ordering",
        source_type="html",
        section_heading=None,
        content_hash="hash_near",
        source_id=source.id,
    )
    await Repository.upsert_chunk(
        session,
        content="far match",
        embedding=far_embedding,
        source_url="https://example.com/ordering",
        source_type="html",
        section_heading=None,
        content_hash="hash_far",
        source_id=source.id,
    )

    results = await Repository.top_k_chunks(session, near_embedding, k=2)

    assert len(results) == 2
    assert results[0].chunk.content == "near match", "Closest chunk should come first"
    assert results[0].score > results[1].score, "Scores should be descending"


async def test_upsert_idempotent_and_updates_on_conflict(session: AsyncSession):
    """Same content_hash twice produces one row, and the second call's values win."""
    source = await Repository.get_or_create_source(
        session,
        name="Idempotent Source",
        url="https://example.com/idempotent",
        source_type="html",
    )

    content_hash = "hash_idempotent_001"
    embedding_v1 = [0.2] * settings.embedding_dim
    embedding_v2 = [0.3] * settings.embedding_dim

    await Repository.upsert_chunk(
        session,
        content="version 1",
        embedding=embedding_v1,
        source_url="https://example.com/idempotent",
        source_type="html",
        section_heading=None,
        content_hash=content_hash,
        source_id=source.id,
    )
    await Repository.upsert_chunk(
        session,
        content="version 2",
        embedding=embedding_v2,
        source_url="https://example.com/idempotent",
        source_type="html",
        section_heading=None,
        content_hash=content_hash,
        source_id=source.id,
    )

    count_result = await session.execute(
        select(func.count()).select_from(ChunkRow).where(ChunkRow.content_hash == content_hash)
    )
    assert count_result.scalar_one() == 1, "Upsert should not create duplicates"

    row_result = await session.execute(
        select(ChunkRow).where(ChunkRow.content_hash == content_hash)
    )
    row = row_result.scalar_one()
    assert row.content == "version 2", "Upsert should update content on conflict"
