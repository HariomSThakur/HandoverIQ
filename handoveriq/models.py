from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    access_level: Mapped[str] = mapped_column(String(16), nullable=False, default="team")
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="upload")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="source", cascade="all, delete-orphan", order_by="Chunk.ordinal"
    )
    claims: Mapped[list["Claim"]] = relationship(back_populates="source")


class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Source] = relationship(back_populates="chunks")
    claims: Mapped[list["Claim"]] = relationship(back_populates="chunk")


class Claim(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"), nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.chunk_id"), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False, default="context")
    owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence_quote: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(16), nullable=False, default="matched")
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    extraction_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )
    source: Mapped[Source] = relationship(back_populates="claims")
    chunk: Mapped[Chunk] = relationship(back_populates="claims")


class ReviewEvent(Base):
    __tablename__ = "review_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
