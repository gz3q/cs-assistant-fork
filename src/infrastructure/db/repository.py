from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.types import Chunk, RetrievedChunk
from src.infrastructure.db.models import ChunkRow, SourceRow


class Repository:
    @staticmethod
    async def has_chunks(session: AsyncSession) -> bool:
        result = await session.execute(select(ChunkRow.id).limit(1))
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_or_create_source(
        session: AsyncSession, *, name: str, url: str, source_type: str
    ) -> SourceRow:
        result = await session.execute(select(SourceRow).where(SourceRow.url == url))
        source = result.scalar_one_or_none()
        if source is None:
            source = SourceRow(name=name, url=url, type=source_type)
            session.add(source)
            await session.flush()
        return source

    @staticmethod
    async def upsert_chunk(
        session: AsyncSession,
        *,
        content: str,
        embedding: list[float],
        source_url: str,
        source_type: str,
        section_heading: str | None,
        content_hash: str,
        source_id: UUID,
    ) -> None:
        stmt = insert(ChunkRow).values(
            content=content,
            embedding=embedding,
            source_url=source_url,
            source_type=source_type,
            section_heading=section_heading,
            content_hash=content_hash,
            source_id=source_id,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["content_hash"],
            set_={
                "content": stmt.excluded.content,
                "embedding": stmt.excluded.embedding,
                "source_url": stmt.excluded.source_url,
                "section_heading": stmt.excluded.section_heading,
            },
        )
        await session.execute(stmt)

    @staticmethod
    async def update_source_synced(session: AsyncSession, source_id: UUID) -> None:
        result = await session.execute(select(SourceRow).where(SourceRow.id == source_id))
        source = result.scalar_one()
        source.last_synced_at = func.now()

    @staticmethod
    async def top_k_chunks(
        session: AsyncSession, query_embedding: list[float], k: int
    ) -> list[RetrievedChunk]:
        distance = ChunkRow.embedding.cosine_distance(query_embedding)
        stmt = select(ChunkRow, distance.label("distance")).order_by(distance).limit(k)
        result = await session.execute(stmt)
        rows = result.all()
        return [
            RetrievedChunk(
                chunk=Chunk(
                    id=row.ChunkRow.id,
                    content=row.ChunkRow.content,
                    source_url=row.ChunkRow.source_url,
                    source_type=row.ChunkRow.source_type,
                    section_heading=row.ChunkRow.section_heading,
                    content_hash=row.ChunkRow.content_hash,
                    scraped_at=row.ChunkRow.scraped_at,
                ),
                score=1.0 - row.distance,
            )
            for row in rows
        ]
