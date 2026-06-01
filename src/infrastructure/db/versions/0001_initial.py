"""initial

Revision ID: 0001
Revises:
Create Date: 2026-05-31

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("CREATE TYPE source_type AS ENUM ('html', 'pointer')")

    op.execute("""
        CREATE TABLE sources (
            id          UUID        PRIMARY KEY,
            name        TEXT        NOT NULL,
            type        source_type NOT NULL,
            url         TEXT        NOT NULL UNIQUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            active      BOOLEAN     NOT NULL DEFAULT TRUE
        )
    """)

    op.execute("""
        CREATE TABLE chunks (
            id              UUID        PRIMARY KEY,
            content         TEXT        NOT NULL,
            embedding       vector(768) NOT NULL,
            source_url      TEXT        NOT NULL,
            source_type     source_type NOT NULL,
            section_heading TEXT,
            content_hash    TEXT        NOT NULL UNIQUE,
            scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            source_id       UUID        NOT NULL REFERENCES sources(id)
        )
    """)

    op.execute("CREATE INDEX ix_chunks_content_hash ON chunks (content_hash)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_content_hash")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS sources")
    op.execute("DROP TYPE IF EXISTS source_type")
    op.execute("DROP EXTENSION IF EXISTS vector")
