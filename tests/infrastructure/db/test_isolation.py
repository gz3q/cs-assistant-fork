from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models import ChunkRow, SourceRow


async def test_database_starts_empty(session: AsyncSession):
    """Confirms the session fixture rolls back between tests.

    If this fails, all other tests are unreliable because data is leaking
    between them. Fix the session fixture before trusting any other result.
    """
    chunk_count = await session.execute(select(func.count()).select_from(ChunkRow))
    source_count = await session.execute(select(func.count()).select_from(SourceRow))
    assert chunk_count.scalar_one() == 0, "Chunks table not empty at test start"
    assert source_count.scalar_one() == 0, "Sources table not empty at test start"
