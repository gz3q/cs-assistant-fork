from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import settings

REPO_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = REPO_ROOT / "src" / "infrastructure" / "db" / "alembic.ini"


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
    """Builds the schema once per session by running Alembic migrations.

    Uses the same migrations as dev/prod (not Base.metadata.create_all) so tests
    exercise the exact DDL that ships, catching model/migration drift. `downgrade
    base` on both ends resets tables AND clears alembic_version (drop_all wouldn't),
    so the next upgrade isn't a no-op.

    WARNING: resets the test database — never point at a DB with real data.
    The safety_check fixture guards against this.
    """
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option(
        "sqlalchemy.url", settings.test_database_url.replace("+asyncpg", "+psycopg2")
    )

    command.downgrade(cfg, "base")  # clean slate; no-op if already empty
    command.upgrade(cfg, "head")

    engine = create_async_engine(settings.test_database_url)
    yield engine
    await engine.dispose()
    command.downgrade(cfg, "base")


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
