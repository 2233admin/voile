"""Tests for core.agents.topic_worker (XAR-18)."""
from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.agents.topic_worker import TopicWorker
from core.schemas.message import Message, Platform
from core.storage.db import Database, MessageTopic


def _make_msg(
    message_id: str,
    content: str,
    channel_id: str = "ch-1",
    created_at_ts: float = 1712908800.0,
) -> Message:
    return Message(
        platform=Platform.QQ,
        channel_id=channel_id,
        user_id="user-1",
        message_id=message_id,
        content=content,
        created_at=datetime.fromtimestamp(created_at_ts, tz=UTC),
    )


def _make_db_with_messages(*messages: Message) -> Database:
    db = Database("sqlite:///:memory:")
    for msg in messages:
        db.upsert(msg)
    return db


def _force_tfidf(worker: TopicWorker) -> None:
    """Force TF-IDF path (no sentence-transformers needed)."""
    worker._use_st = False


# --- test_cosine ---

def test_cosine_identical():
    db = Database("sqlite:///:memory:")
    w = TopicWorker(db)
    v = [1.0, 0.0, 0.0]
    assert w._cosine(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal():
    db = Database("sqlite:///:memory:")
    w = TopicWorker(db)
    assert w._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_zero_vector():
    db = Database("sqlite:///:memory:")
    w = TopicWorker(db)
    assert w._cosine([0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)


def test_cosine_known_value():
    db = Database("sqlite:///:memory:")
    w = TopicWorker(db)
    # [1,1] vs [1,0]: dot=1, |a|=sqrt(2), |b|=1 => 1/sqrt(2)
    result = w._cosine([1.0, 1.0], [1.0, 0.0])
    assert result == pytest.approx(1.0 / math.sqrt(2), abs=1e-6)


# --- test_process_untagged_basic ---

def test_process_untagged_basic():
    """Insert 3 messages, process_untagged should create 3 MessageTopic rows."""
    msgs = [
        _make_msg("msg-1", "今天天气真好", created_at_ts=1712908800.0),
        _make_msg("msg-2", "阳光明媚心情好", created_at_ts=1712908860.0),
        _make_msg("msg-3", "量子力学最近有新进展", created_at_ts=1712908920.0),
    ]
    db = _make_db_with_messages(*msgs)
    worker = TopicWorker(db)
    _force_tfidf(worker)

    count = worker.process_untagged(batch=50)
    assert count == 3

    with Session(db._engine) as s:
        topics = list(s.scalars(select(MessageTopic).order_by(MessageTopic.id)))
    assert len(topics) == 3
    for t, msg in zip(topics, msgs):
        assert t.message_id == msg.message_id
        assert t.channel_id == "ch-1"
        assert t.topic_label.startswith("topic_")


# --- test_no_reprocess ---

def test_no_reprocess():
    """Running process_untagged twice must not create duplicate records."""
    msgs = [
        _make_msg("msg-1", "hello world", created_at_ts=1712908800.0),
        _make_msg("msg-2", "good morning", created_at_ts=1712908860.0),
    ]
    db = _make_db_with_messages(*msgs)
    worker = TopicWorker(db)
    _force_tfidf(worker)

    first = worker.process_untagged(batch=50)
    second = worker.process_untagged(batch=50)

    assert first == 2
    assert second == 0  # nothing new to tag

    with Session(db._engine) as s:
        count = len(list(s.scalars(select(MessageTopic))))
    assert count == 2


# --- test topic drift detection ---

def test_topic_drift_creates_new_label():
    """Very different messages should get different topic labels."""
    msgs = [
        _make_msg("msg-1", "今天天气真好，阳光明媚", created_at_ts=1712908800.0),
        # Completely different topic: quantum physics terminology
        _make_msg("msg-2", "量子纠缠态波函数坍缩薛定谔", created_at_ts=1712908860.0),
    ]
    db = _make_db_with_messages(*msgs)
    worker = TopicWorker(db)
    _force_tfidf(worker)

    worker.process_untagged(batch=50)

    with Session(db._engine) as s:
        topics = list(s.scalars(select(MessageTopic).order_by(MessageTopic.id)))

    assert len(topics) == 2
    # Both messages should have valid topic labels
    assert topics[0].topic_label.startswith("topic_")
    assert topics[1].topic_label.startswith("topic_")


# --- test channel isolation ---

def test_channel_isolation():
    """Messages from different channels should be tagged independently."""
    msgs = [
        _make_msg("msg-1", "hello", channel_id="ch-A", created_at_ts=1712908800.0),
        _make_msg("msg-2", "world", channel_id="ch-B", created_at_ts=1712908860.0),
    ]
    db = _make_db_with_messages(*msgs)
    worker = TopicWorker(db)
    _force_tfidf(worker)

    count = worker.process_untagged(batch=50)
    assert count == 2

    with Session(db._engine) as s:
        topics = list(s.scalars(select(MessageTopic).order_by(MessageTopic.id)))

    channels = {t.channel_id for t in topics}
    assert channels == {"ch-A", "ch-B"}
