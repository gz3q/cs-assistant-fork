from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.config import settings


async def test_embedding_column_dim_matches_settings(db_engine: AsyncEngine):
    """The migrated embedding column must be vector(settings.embedding_dim).

    The column dimension is hardcoded in the migration while the model and
    embedding pipeline read settings.embedding_dim. If they diverge, inserts
    fail against the real schema -- this asserts they agree at build time.
    """
    async with db_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT format_type(atttypid, atttypmod) "
                "FROM pg_attribute "
                "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
            )
        )
        column_type = result.scalar_one()

    assert column_type == f"vector({settings.embedding_dim})"
