"""XAR-18: Topic drift detection worker."""
from __future__ import annotations

import logging
import math
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.storage.db import Database, MessageRecord, MessageTopic

SIMILARITY_THRESHOLD = 0.5  # below this = topic drift

logger = logging.getLogger(__name__)


def _try_import_sentence_transformers() -> Any:
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer
    except ImportError:
        return None


class TopicWorker:
    def __init__(
        self,
        db: Database,
        channel_id: str | None = None,
        obsidian_vault: str | None = None,
        ann_addr: str | None = None,
    ) -> None:
        self.db = db
        self.channel_id = channel_id
        self.obsidian_vault = obsidian_vault
        self.ann_addr = ann_addr
        self._model: Any = None
        self._use_st: bool | None = None  # None = not yet detected
        self._ann_stub: Any = None
        self._pb2: Any = None
        self._ann_ok = False
        self._ann_disabled = False  # set on first failure; blocks all retries

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
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4))
        matrix = vectorizer.fit_transform(texts)
        return matrix.toarray().tolist()  # type: ignore[no-any-return]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _init_ann(self) -> None:
        if self._ann_ok or self._ann_disabled or self.ann_addr is None:
            return
        try:
            import grpc

            from core.gen import voile_pb2, voile_pb2_grpc
            channel = grpc.insecure_channel(self.ann_addr)
            self._ann_stub = voile_pb2_grpc.VectorIndexStub(channel)  # type: ignore[no-untyped-call]
            self._pb2 = voile_pb2
            self._ann_ok = True
            logger.info("ann connected at %s", self.ann_addr)
        except Exception as exc:
            logger.debug("ann unavailable (%s), using in-process cosine", exc)
            self._ann_disabled = True

    def _ann_similarity(self, embed: list[float]) -> tuple[str, float] | None:
        """Query ann for nearest neighbour. Returns (id, score) or None."""
        self._init_ann()
        if not self._ann_ok or self._ann_stub is None:
            return None
        try:
            resp = self._ann_stub.Search(
                self._pb2.SearchRequest(
                    query=self._pb2.Vector(values=embed),
                    top_k=1,
                    threshold=SIMILARITY_THRESHOLD,
                )
            )
            if resp.results:
                r = resp.results[0]
                return r.id, r.score
            return None
        except Exception as exc:
            logger.warning("ann search failed: %s", exc)
            self._ann_ok = False
            self._ann_disabled = True
            return None

    def _ann_insert(self, msg_id: str, embed: list[float]) -> None:
        if not self._ann_ok or self._ann_stub is None:
            return
        try:
            self._ann_stub.Insert(
                self._pb2.InsertRequest(
                    id=msg_id,
                    vector=self._pb2.Vector(values=embed),
                )
            )
        except Exception as exc:
            logger.warning("ann insert failed: %s", exc)
            self._ann_ok = False
            self._ann_disabled = True

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
                        ann_hit = self._ann_similarity(cur_embed)
                        sim = (
                            ann_hit[1] if ann_hit is not None
                            else self._cosine(prev_embed, cur_embed)
                        )
                        if sim < SIMILARITY_THRESHOLD:
                            # Topic drift: finalize card for the closing topic
                            if prev_label is not None and self.obsidian_vault is not None:
                                self._finalize_topic_card(prev_label, ch_id, session)
                            ts = int(msg.created_at.timestamp())
                            topic_label = f"topic_{ts}"
                            segment_start = msg.message_id
                        else:
                            # Continue current topic
                            assert prev_label is not None
                            topic_label = prev_label
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
                    self._ann_insert(msg.message_id, cur_embed)

                    prev_embed = cur_embed
                    prev_label = topic_label
                    prev_msg_id = msg.message_id
                    total += 1

                # Write / refresh card for still-open topic at end of batch
                if prev_label is not None and self.obsidian_vault is not None:
                    self._finalize_topic_card(prev_label, ch_id, session)

            session.commit()
            return total

    def _finalize_topic_card(self, topic_label: str, channel_id: str, session: Session) -> None:
        """Write/overwrite Obsidian topic card with all messages when topic closes."""
        import os
        import re as _re

        if self.obsidian_vault is None:
            return

        # autoflush sees uncommitted batch records
        msg_ids = list(session.scalars(
            select(MessageTopic.message_id)
            .where(MessageTopic.topic_label == topic_label)
            .where(MessageTopic.channel_id == channel_id)
        ))
        if not msg_ids:
            return

        messages = list(session.scalars(
            select(MessageRecord)
            .where(MessageRecord.message_id.in_(msg_ids))
            .order_by(MessageRecord.created_at.asc())
        ))
        if not messages:
            return

        first = messages[0]
        last = messages[-1]
        participants = sorted({m.user_id for m in messages if m.user_id})
        all_urls: list[str] = []
        seen_urls: set[str] = set()
        for m in messages:
            for u in (m.urls or []):
                if u not in seen_urls:
                    all_urls.append(u)
                    seen_urls.add(u)

        # Resolve link titles for [[wikilinks]]
        link_names: dict[str, str] = {}
        if all_urls:
            from core.storage.db import LinkRecord
            for rec in session.scalars(select(LinkRecord).where(LinkRecord.url.in_(all_urls))):
                if rec.title:
                    slug = _re.sub(r"[^a-z0-9]+", "-", rec.title.lower()).strip("-")[:80]
                    link_names[rec.url] = slug

        date = first.created_at.strftime("%Y-%m-%d")
        started_at = first.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        ended_at = last.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "---",
            f"date: {date}",
            f"topic: {topic_label}",
            f"channel: {channel_id}",
            f"started_at: {started_at}",
            f"ended_at: {ended_at}",
            f"message_count: {len(messages)}",
            f"participants: [{', '.join(participants)}]",
            "tags:",
            "  - voile/topic",
            "---",
            "",
            f"# {topic_label}",
            "",
            "## Messages",
            "",
        ]

        for m in messages[:20]:
            ts = m.created_at.strftime("%H:%M")
            speaker = m.user_id or "unknown"
            lines.append(f"> **{speaker}** {ts}: {m.content}")
        if len(messages) > 20:
            lines.append(f"> *...{len(messages) - 20} more messages*")
        lines.append("")

        if all_urls:
            lines += ["## Related Links", ""]
            for url in all_urls[:10]:
                name = link_names.get(url)
                lines.append(f"- [[{name}]]" if name else f"- {url}")
            lines.append("")

        topics_dir = os.path.join(self.obsidian_vault, "topics")
        os.makedirs(topics_dir, exist_ok=True)
        safe_label = topic_label.replace("/", "_")
        path = os.path.join(topics_dir, f"{safe_label}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def run_forever(self, sleep: float = 5.0) -> None:
        while True:
            self.process_untagged()
            time.sleep(sleep)
