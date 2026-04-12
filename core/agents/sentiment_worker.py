"""XAR-19: Sentiment analysis worker for chat messages."""
from __future__ import annotations

import time
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.storage.db import Database, MessageRecord, MessageSentiment

# ---------------------------------------------------------------------------
# Rule-based fallback lexicon (30 words each)
# ---------------------------------------------------------------------------

POSITIVE = {
    "好", "棒", "赞", "不错", "优秀", "开心", "感谢", "支持", "喜欢", "厉害",
    "完美", "太好了", "很好", "牛", "强", "漂亮", "成功", "高兴", "满意", "给力",
    "太棒了", "超级", "幸福", "顺利", "精彩", "推荐", "正确", "对", "可以", "认可",
}

NEGATIVE = {
    "差", "烂", "垃圾", "糟糕", "讨厌", "失望", "问题", "错误", "坏", "难受",
    "可恶", "恶心", "生气", "崩溃", "无语", "扯淡", "坑", "害怕", "痛苦", "失败",
    "不行", "不好", "太差", "很差", "麻烦", "困难", "担心", "焦虑", "后悔", "抱怨",
}


def _rule_analyze(text: str) -> tuple[str, float]:
    """Rule-based sentiment via word counting."""
    pos = sum(1 for w in POSITIVE if w in text)
    neg = sum(1 for w in NEGATIVE if w in text)
    total = pos + neg
    if total == 0:
        return "neutral", 0.5
    score = pos / total
    if score > 0.6:
        return "positive", score
    if score < 0.4:
        return "negative", 1.0 - score
    return "neutral", 0.5


class SentimentWorker:
    def __init__(self, db: Database, obsidian_vault: str | None = None):
        self.db = db
        self.obsidian_vault = obsidian_vault
        self._pipeline = None
        self._backend: str = self._detect_backend()

    # ------------------------------------------------------------------
    # Backend detection (run once at init)
    # ------------------------------------------------------------------

    def _detect_backend(self) -> str:
        try:
            from transformers import pipeline as hf_pipeline  # type: ignore
            self._pipeline = hf_pipeline(
                "text-classification",
                model="IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment",
            )
            return "transformers"
        except Exception:
            pass
        try:
            import snownlp  # type: ignore  # noqa: F401
            return "snownlp"
        except Exception:
            pass
        return "rules"

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def _analyze(self, text: str) -> tuple[str, float]:
        """Returns (label, score). label in {positive, negative, neutral}."""
        if self._backend == "transformers" and self._pipeline is not None:
            result = self._pipeline(text[:512])[0]
            raw_label: str = result["label"].lower()
            score: float = float(result["score"])
            # Erlangshen outputs "positive"/"negative"; normalise just in case
            if "pos" in raw_label:
                return "positive", score
            if "neg" in raw_label:
                return "negative", score
            return "neutral", score

        if self._backend == "snownlp":
            from snownlp import SnowNLP  # type: ignore
            s = SnowNLP(text)
            sentiment: float = s.sentiments
            if sentiment > 0.6:
                return "positive", sentiment
            if sentiment < 0.4:
                return "negative", 1.0 - sentiment
            return "neutral", 0.5

        return _rule_analyze(text)

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def process_untagged(self, batch: int = 100) -> int:
        """Tag messages not yet in message_sentiments. Returns count processed."""
        with Session(self.db._engine) as session:
            tagged_ids_subq = select(MessageSentiment.message_id)
            rows = list(session.scalars(
                select(MessageRecord)
                .where(MessageRecord.message_id.not_in(tagged_ids_subq))
                .limit(batch)
            ))

            if not rows:
                return 0

            now = datetime.now(tz=UTC)
            for row in rows:
                label, score = self._analyze(row.content)
                session.add(MessageSentiment(
                    message_id=row.message_id,
                    label=label,
                    score=score,
                    created_at=now,
                ))
            session.commit()
            return len(rows)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def daily_report(self, channel_id: str, date: str) -> dict:
        """Aggregate sentiment for channel on date (YYYY-MM-DD).

        Returns {positive: N, negative: N, neutral: N}.
        """
        with Session(self.db._engine) as session:
            # Join messages -> sentiments, filter by channel + date prefix
            rows = list(session.execute(
                select(MessageSentiment.label)
                .join(MessageRecord, MessageRecord.message_id == MessageSentiment.message_id)
                .where(MessageRecord.channel_id == channel_id)
                .where(func.date(MessageRecord.created_at) == date)
            ))

        counts: dict[str, int] = {"positive": 0, "negative": 0, "neutral": 0}
        for (label,) in rows:
            if label in counts:
                counts[label] += 1
        return counts

    # ------------------------------------------------------------------
    # Long-running loop
    # ------------------------------------------------------------------

    def run_forever(self, sleep: float = 10.0) -> None:
        while True:
            self.process_untagged()
            time.sleep(sleep)
