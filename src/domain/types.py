from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: UUID
    content: str
    source_url: str
    source_type: Literal["html", "pointer"]
    section_heading: str | None
    content_hash: str
    scraped_at: datetime


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    chunk: Chunk
    score: float


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    url: str
    title: str | None


class Answer(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    text: str
    sources: list[Source]
    confidence: Literal["high", "low", "abstain"]
