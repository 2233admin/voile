"""XAR-18: Topic drift detection worker."""
from __future__ import annotations

import math
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.storage.db import Database, MessageRecord, MessageTopic

SIMILARITY_THRESHOLD = 0.5  # below this = topic drift


def _try_import_sentence_transformers() -> Any:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import]
        return SentenceTransformer
    except ImportError:
        return None


class TopicWorker:
    def __init__(
        self,
        db: Database,
        channel_id: str | None = None,
        obsidian_vault: str | None = None,
    ) -> None:
        self.db = db
        self.channel_id = channel_id
        self.obsidian_vault = obsidian_vault
        self._model: Any = None
        self._use_st: bool | None = None  # None = not yet detected

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Returns embeddings. Tries sentence-transformers, falls back to TF-IDF."""
        if self._use_st is None:
            SentenceTransformer = _try_import_sentence_transformers()
            if SentenceTransformer is not None:
                self._model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
                self._use_st = True
            else:
                self._use_st = False

        if self._use_st and self._model is not None:
            vecs = self._model.encode(texts, convert_to_numpy=True)
            return [v.tolist() for v in vecs]

        # TF-IDF fallback
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import]

        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4))
        matrix = vectorizer.fit_transform(texts)
        return matrix.toarray().tolist()

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def process_untagged(self, batch: int = 50) -> int:
        """Find messages not in message_topics, tag them. Returns count processed."""
        with Session(self.db._engine) as session:
            # Query messages that have no corresponding message_topics record
            tagged_subq = select(MessageTopic.message_id)
            query = (
                select(MessageRecord)
                .where(MessageRecord.message_id.not_in(tagged_subq))
            )
            if self.channel_id is not None:
                query = query.where(MessageRecord.channel_id == self.channel_id)
            query = query.order_by(MessageRecord.created_at.asc()).limit(batch)

            rows: list[MessageRecord] = list(session.scalars(query))
            if not rows:
                return 0

            # Group by channel_id
            channels: dict[str, list[MessageRecord]] = {}
            for row in rows:
                channels.setdefault(row.channel_id, []).append(row)

            total = 0
            for ch_id, msgs in channels.items():
                # Need the last tagged message for this channel to seed the window
                last_tagged = session.scalar(
                    select(MessageTopic)
                    .where(MessageTopic.channel_id == ch_id)
                    .order_by(MessageTopic.created_at.desc())
                    .limit(1)
                )

                prev_label: str | None = last_tagged.topic_label if last_tagged else None
                prev_msg_id: str | None = last_tagged.message_id if last_tagged else None
                prev_embed: list[float] | None = None

                # If there was a previous message, get its embedding seed
                if last_tagged is not None:
                    prev_record = session.scalar(
                        select(MessageRecord)
                        .where(MessageRecord.message_id == last_tagged.message_id)
                    )
                    if prev_record is not None:
                        prev_embed = self._embed([prev_record.content])[0]

                for msg in msgs:
                    cur_embed = self._embed([msg.content])[0]

                    if prev_embed is None:
                        # First message in channel — start a new topic
                        ts = int(msg.created_at.timestamp())
                        topic_label = f"topic_{ts}"
                        segment_start = msg.message_id
                        sim = 0.0
                    else:
                        sim = self._cosine(prev_embed, cur_embed)
                        if sim < SIMILARITY_THRESHOLD:
                            # Topic drift
                            ts = int(msg.created_at.timestamp())
                            topic_label = f"topic_{ts}"
                            segment_start = msg.message_id
                        else:
                            # Continue current topic
                            assert prev_label is not None
                            topic_label = prev_label
                            # segment_start: find from last tagged that shares this label
                            segment_start = prev_msg_id or msg.message_id

                    record = MessageTopic(
                        message_id=msg.message_id,
                        channel_id=ch_id,
                        topic_label=topic_label,
                        segment_start=segment_start,
                        similarity_score=sim,
                        created_at=msg.created_at,
                    )
                    session.add(record)

                    # Write Obsidian card on new topic
                    if (
                        self.obsidian_vault is not None
                        and (prev_label is None or topic_label != prev_label)
                    ):
                        self._write_topic_card(topic_label, msg)

                    prev_embed = cur_embed
                    prev_label = topic_label
                    prev_msg_id = msg.message_id
                    total += 1

            session.commit()
            return total

    def _write_topic_card(self, topic_label: str, msg: MessageRecord) -> None:
        """Write a minimal Obsidian markdown card for a new topic segment."""
        import os

        if self.obsidian_vault is None:
            return
        topics_dir = os.path.join(self.obsidian_vault, "topics")
        os.makedirs(topics_dir, exist_ok=True)
        safe_label = topic_label.replace("/", "_")
        path = os.path.join(topics_dir, f"{safe_label}.md")
        if not os.path.exists(path):
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {topic_label}\n\n")
                f.write(f"- channel: {msg.channel_id}\n")
                f.write(f"- started_at: {ts}\n")
                f.write(f"- first_message: {msg.message_id}\n")

    def run_forever(self, sleep: float = 5.0) -> None:
        while True:
            self.process_untagged()
            time.sleep(sleep)
