from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.config import settings

# Shared enum object — SQLAlchemy creates/drops the Postgres type exactly once.
source_type_enum = SAEnum("html", "pointer", name="source_type")


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str]
    type: Mapped[str] = mapped_column(source_type_enum)
    url: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    active: Mapped[bool] = mapped_column(default=True)

    chunks: Mapped[list["ChunkRow"]] = relationship(back_populates="source")


class ChunkRow(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    content: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
    source_url: Mapped[str]
    source_type: Mapped[str] = mapped_column(source_type_enum)
    section_heading: Mapped[str | None]
    content_hash: Mapped[str] = mapped_column(unique=True, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"))
    source: Mapped["SourceRow"] = relationship(back_populates="chunks")
