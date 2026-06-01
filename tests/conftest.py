import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import settings
from src.infrastructure.db.models import Base


@pytest.fixture(scope="session", autouse=True)
def safety_check():
    """Refuse to run tests against anything that doesn't look like a test database.

    Tests use drop_all/create_all which would destroy real data.
    """
    url = settings.test_database_url
    if url is None:
        pytest.exit(
            "Refusing to run tests: TEST_DATABASE_URL is not set. "
            "Copy .env.example to .env and configure it.",
            returncode=1,
        )
    if "test" not in url.lower():
        pytest.exit(
            f"Refusing to run tests: TEST_DATABASE_URL does not contain 'test'. "
            f"Got: {url}. Safety check to prevent dropping production data.",
            returncode=1,
        )
    if url == settings.database_url:
        pytest.exit(
            "Refusing to run tests: TEST_DATABASE_URL == DATABASE_URL. "
            "Tests would destroy dev data.",
            returncode=1,
        )


@pytest.fixture(scope="session")
async def db_engine():
    """Creates tables once per test session; drops them on teardown.

    WARNING: resets the test database — never point at a DB with real data.
    The safety_check fixture guards against this.
    """
    engine = create_async_engine(settings.test_database_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(db_engine):
    """Session bound to a transaction that's rolled back after each test."""
    async with db_engine.connect() as conn:
        trans = await conn.begin()
        s = AsyncSession(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield s
        finally:
            await s.close()
            await trans.rollback()
