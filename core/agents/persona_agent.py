"""XAR-20: Persona Agent -- aggregate per-user message history into Core profiles."""
from __future__ import annotations

import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.storage.db import Database, MessageRecord, MessageSentiment, MessageTopic


class PersonaAgent:
    def __init__(
        self,
        db: Database,
        channel_id: str | None = None,
        obsidian_vault: str | None = None,
        window_days: int = 30,
    ) -> None:
        self.db = db
        self.channel_id = channel_id
        self.obsidian_vault = obsidian_vault
        self.window_days = window_days

    # ------------------------------------------------------------------
    # Profile building
    # ------------------------------------------------------------------

    def build_profile(self, user_id: str) -> dict[str, Any]:
        """Aggregate last window_days of messages for user_id into a Core profile."""
        cutoff = datetime.now(tz=UTC) - timedelta(days=self.window_days)

        with Session(self.db._engine) as session:
            messages: list[MessageRecord] = list(session.scalars(
                select(MessageRecord)
                .where(MessageRecord.channel_id == self.channel_id)
                .where(MessageRecord.user_id == user_id)
                .where(MessageRecord.created_at >= cutoff)
                .order_by(MessageRecord.created_at.desc())
            ))

            message_ids = [m.message_id for m in messages]

            # --- top_topics (from message_topics, by frequency) ---
            top_topics: list[str] = []
            if message_ids:
                topic_rows = list(session.scalars(
                    select(MessageTopic.topic_label)
                    .where(MessageTopic.message_id.in_(message_ids))
                ))
                counter = Counter(topic_rows)
                top_topics = [label for label, _ in counter.most_common(5)]

            # --- sentiment_trend ---
            sentiment_trend = "neutral"
            if message_ids:
                sentiment_rows = list(session.scalars(
                    select(MessageSentiment.label)
                    .where(MessageSentiment.message_id.in_(message_ids))
                ))
                if sentiment_rows:
                    counts = Counter(sentiment_rows)
                    sentiment_trend = counts.most_common(1)[0][0]

            # --- message_count ---
            message_count = len(messages)

            # --- active_hours (peak hours by message count, top 3) ---
            hour_counter: Counter[int] = Counter()
            for msg in messages:
                dt = msg.created_at
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                hour_counter[dt.hour] += 1
            active_hours: list[int] = [h for h, _ in hour_counter.most_common(3)]

            # --- sample_quotes (up to 3 most recent non-empty content strings) ---
            sample_quotes: list[str] = []
            for msg in messages:
                if msg.content and msg.content.strip():
                    sample_quotes.append(msg.content.strip())
                if len(sample_quotes) >= 3:
                    break

        return {
            "top_topics": top_topics,
            "sentiment_trend": sentiment_trend,
            "message_count": message_count,
            "active_hours": active_hours,
            "sample_quotes": sample_quotes,
        }

    # ------------------------------------------------------------------
    # Run methods
    # ------------------------------------------------------------------

    def run_once(self, channel_id: str | None = None) -> list[str]:
        """Build and write profiles for all distinct users in channel_id.

        Returns list of user_ids processed.
        """
        ch = channel_id or self.channel_id
        if ch is None:
            return []

        with Session(self.db._engine) as session:
            user_ids: list[str] = list(session.scalars(
                select(MessageRecord.user_id)
                .where(MessageRecord.channel_id == ch)
                .distinct()
            ))

        for user_id in user_ids:
            profile = self.build_profile(user_id)
            if self.obsidian_vault is not None:
                from core.obsidian.writer import ObsidianWriter
                writer = ObsidianWriter(self.obsidian_vault)
                writer.write_persona(user_id, profile)

        return user_ids

    def run_forever(self, sleep: float = 86400.0) -> None:
        """Loop: call run_once() then sleep for sleep seconds."""
        while True:
            self.run_once()
            time.sleep(sleep)
