"""Tests for core.agents.sentiment_worker (XAR-19)."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import ModuleType
from unittest.mock import patch

import pytest

from core.schemas.message import Message, Platform
from core.storage.db import Database, MessageRecord, MessageSentiment
from sqlalchemy.orm import Session
from sqlalchemy import select


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> Database:
    return Database("sqlite:///:memory:")


def _insert_msg(
    db: Database,
    message_id: str = "msg-1",
    content: str = "今天真的很好很开心",
    channel_id: str = "ch-1",
    ts: float = 1712908800.0,
) -> None:
    db.upsert(Message(
        platform=Platform.QQ,
        channel_id=channel_id,
        user_id="u1",
        message_id=message_id,
        content=content,
        created_at=datetime.fromtimestamp(ts, tz=timezone.utc),
    ))


def _insert_sentiment(db: Database, message_id: str, label: str, score: float = 0.8) -> None:
    with Session(db._engine) as s:
        s.add(MessageSentiment(
            message_id=message_id,
            label=label,
            score=score,
            created_at=datetime.now(tz=timezone.utc),
        ))
        s.commit()


# ---------------------------------------------------------------------------
# Fixtures that force the rules backend regardless of installed packages
# ---------------------------------------------------------------------------

@pytest.fixture()
def rules_worker():
    """Return a SentimentWorker pinned to the rule-based fallback."""
    # Block transformers and snownlp so _detect_backend falls through to rules
    with patch.dict(sys.modules, {"transformers": None, "snownlp": None}):
        from core.agents.sentiment_worker import SentimentWorker
        db = _make_db()
        worker = SentimentWorker.__new__(SentimentWorker)
        worker.db = db
        worker.obsidian_vault = None
        worker._pipeline = None
        worker._backend = "rules"
        yield worker


# ---------------------------------------------------------------------------
# test_analyze_fallback: rule engine only, no external deps
# ---------------------------------------------------------------------------

class TestAnalyzeFallback:
    def test_positive_text(self, rules_worker):
        label, score = rules_worker._analyze("今天真的很好，感谢支持，太棒了")
        assert label == "positive"
        assert 0.0 <= score <= 1.0

    def test_negative_text(self, rules_worker):
        label, score = rules_worker._analyze("这个垃圾产品太差了，真的很失望")
        assert label == "negative"
        assert 0.0 <= score <= 1.0

    def test_neutral_text(self, rules_worker):
        label, score = rules_worker._analyze("今天下午三点开会")
        assert label == "neutral"

    def test_empty_text(self, rules_worker):
        label, score = rules_worker._analyze("")
        assert label == "neutral"


# ---------------------------------------------------------------------------
# test_process_untagged: insert messages, process, check sentiments written
# ---------------------------------------------------------------------------

class TestProcessUntagged:
    def test_process_untagged_creates_records(self, rules_worker):
        db = rules_worker.db
        _insert_msg(db, "m1", "很好很棒")
        _insert_msg(db, "m2", "很差很烂")

        count = rules_worker.process_untagged()
        assert count == 2

        with Session(db._engine) as s:
            records = list(s.scalars(select(MessageSentiment)))
        assert len(records) == 2
        ids = {r.message_id for r in records}
        assert ids == {"m1", "m2"}
        labels = {r.message_id: r.label for r in records}
        assert labels["m1"] in {"positive", "neutral", "negative"}
        assert labels["m2"] in {"positive", "neutral", "negative"}

    def test_process_empty_returns_zero(self, rules_worker):
        assert rules_worker.process_untagged() == 0

    def test_batch_limit(self, rules_worker):
        db = rules_worker.db
        for i in range(5):
            _insert_msg(db, f"m{i}", "好棒")

        count = rules_worker.process_untagged(batch=3)
        assert count == 3

        with Session(db._engine) as s:
            total = len(list(s.scalars(select(MessageSentiment))))
        assert total == 3


# ---------------------------------------------------------------------------
# test_no_reprocess: duplicate runs don't create extra records
# ---------------------------------------------------------------------------

class TestNoReprocess:
    def test_no_reprocess(self, rules_worker):
        db = rules_worker.db
        _insert_msg(db, "m1", "很好")

        count1 = rules_worker.process_untagged()
        count2 = rules_worker.process_untagged()

        assert count1 == 1
        assert count2 == 0  # already tagged, nothing to do

        with Session(db._engine) as s:
            rows = list(s.scalars(select(MessageSentiment)))
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# test_daily_report: aggregate by channel + date
# ---------------------------------------------------------------------------

class TestDailyReport:
    def test_daily_report_counts(self, rules_worker):
        db = rules_worker.db
        # Insert messages on 2024-04-12
        ts = datetime(2024, 4, 12, 10, 0, 0, tzinfo=timezone.utc).timestamp()
        _insert_msg(db, "m1", "text1", channel_id="ch-1", ts=ts)
        _insert_msg(db, "m2", "text2", channel_id="ch-1", ts=ts)
        _insert_msg(db, "m3", "text3", channel_id="ch-1", ts=ts)
        # One message on a different day
        ts2 = datetime(2024, 4, 13, 10, 0, 0, tzinfo=timezone.utc).timestamp()
        _insert_msg(db, "m4", "text4", channel_id="ch-1", ts=ts2)

        # Manually insert sentiments
        _insert_sentiment(db, "m1", "positive")
        _insert_sentiment(db, "m2", "negative")
        _insert_sentiment(db, "m3", "neutral")
        _insert_sentiment(db, "m4", "positive")

        result = rules_worker.daily_report("ch-1", "2024-04-12")

        assert result["positive"] == 1
        assert result["negative"] == 1
        assert result["neutral"] == 1
        # m4 is on 2024-04-13, must not appear
        assert sum(result.values()) == 3

    def test_daily_report_empty(self, rules_worker):
        result = rules_worker.daily_report("no-such-channel", "2024-01-01")
        assert result == {"positive": 0, "negative": 0, "neutral": 0}

    def test_daily_report_wrong_channel(self, rules_worker):
        db = rules_worker.db
        ts = datetime(2024, 4, 12, 10, 0, 0, tzinfo=timezone.utc).timestamp()
        _insert_msg(db, "m1", "很好", channel_id="ch-A", ts=ts)
        _insert_sentiment(db, "m1", "positive")

        result = rules_worker.daily_report("ch-B", "2024-04-12")
        assert result == {"positive": 0, "negative": 0, "neutral": 0}
