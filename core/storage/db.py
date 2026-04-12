"""XAR-13: SQLAlchemy 2.0 storage abstraction (SQLite dev / Postgres prod)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core.schemas import Message


class Base(DeclarativeBase):
    pass


class MessageRecord(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    channel_id: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True)
    message_type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    urls: Mapped[list[str]] = mapped_column(JSON, default=list)


class Database:
    def __init__(self, url: str = "sqlite:///voile.db") -> None:
        self._engine = create_engine(url, echo=False)
        Base.metadata.create_all(self._engine)

    def upsert(self, msg: Message) -> bool:
        """Insert message; skip if message_id already exists. Returns True on insert."""
        with Session(self._engine) as s:
            existing = s.scalar(
                select(MessageRecord).where(MessageRecord.message_id == msg.message_id)
            )
            if existing:
                return False
            s.add(MessageRecord(
                platform=msg.platform,
                channel_id=msg.channel_id,
                user_id=msg.user_id,
                message_id=msg.message_id,
                message_type=msg.message_type,
                content=msg.content,
                raw_payload=msg.raw_payload,
                created_at=msg.created_at,
                urls=msg.urls,
            ))
            s.commit()
            return True

    def recent(self, channel_id: str, limit: int = 100) -> list[MessageRecord]:
        with Session(self._engine) as s:
            return list(s.scalars(
                select(MessageRecord)
                .where(MessageRecord.channel_id == channel_id)
                .order_by(MessageRecord.created_at.desc())
                .limit(limit)
            ))


class LinkRecord(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    obsidian_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class MessageTopic(Base):
    __tablename__ = "message_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(255), index=True)
    channel_id: Mapped[str] = mapped_column(String(255), index=True)
    topic_label: Mapped[str] = mapped_column(String(500))
    segment_start: Mapped[str] = mapped_column(String(255))  # message_id of segment start
    similarity_score: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MessageSentiment(Base):
    __tablename__ = "message_sentiments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(20))     # positive / negative / neutral
    score: Mapped[float] = mapped_column(default=0.0)  # confidence [0,1]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
