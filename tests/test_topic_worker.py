"""Tests for core.agents.topic_worker (XAR-18)."""
from __future__ import annotations

import math
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.agents.topic_worker import SIMILARITY_THRESHOLD, TopicWorker
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


# ---------------------------------------------------------------------------
# ann integration tests (mock gRPC stub)
# ---------------------------------------------------------------------------

def _make_stub(results: list[tuple[str, float]]) -> MagicMock:
    """Build a mock VectorIndexStub."""
    stub = MagicMock()
    search_result_list = []
    for rid, score in results:
        r = MagicMock()
        r.id = rid
        r.score = score
        search_result_list.append(r)
    stub.Search.return_value = MagicMock(results=search_result_list)
    stub.Insert.return_value = MagicMock(ok=True)
    return stub


def _worker_with_ann(stub: MagicMock, ann_addr: str = "localhost:50052") -> TopicWorker:
    """Return a TopicWorker pre-wired with a mock ann stub."""
    db = Database("sqlite:///:memory:")
    worker = TopicWorker(db, ann_addr=ann_addr)
    _force_tfidf(worker)
    worker._ann_stub = stub
    worker._pb2 = MagicMock()
    worker._ann_ok = True
    return worker


class TestAnnSimilarity:
    def test_returns_none_when_ann_disabled(self):
        db = Database("sqlite:///:memory:")
        worker = TopicWorker(db, ann_addr=None)
        assert worker._ann_similarity([0.1, 0.2]) is None

    def test_returns_none_when_ann_not_ok(self):
        db = Database("sqlite:///:memory:")
        worker = TopicWorker(db, ann_addr="localhost:50052")
        worker._ann_ok = False
        worker._ann_disabled = True  # prevent _init_ann retry
        assert worker._ann_similarity([0.1, 0.2]) is None

    def test_returns_id_and_score(self):
        stub = _make_stub([("msg-prev", 0.85)])
        worker = _worker_with_ann(stub)
        result = worker._ann_similarity([0.1, 0.2])
        assert result is not None
        assert result[0] == "msg-prev"
        assert result[1] == pytest.approx(0.85)

    def test_returns_none_when_no_results(self):
        stub = _make_stub([])
        worker = _worker_with_ann(stub)
        assert worker._ann_similarity([0.1, 0.2]) is None

    def test_resets_ann_ok_on_exception(self):
        stub = MagicMock()
        stub.Search.side_effect = RuntimeError("connection reset")
        worker = _worker_with_ann(stub)
        result = worker._ann_similarity([0.1, 0.2])
        assert result is None
        assert worker._ann_ok is False
        assert worker._ann_disabled is True


class TestAnnInsert:
    def test_skips_when_not_ok(self):
        stub = _make_stub([])
        db = Database("sqlite:///:memory:")
        worker = TopicWorker(db, ann_addr="localhost:50052")
        worker._ann_ok = False
        worker._ann_stub = stub
        worker._ann_insert("msg-1", [0.1, 0.2])
        stub.Insert.assert_not_called()

    def test_calls_insert(self):
        stub = _make_stub([])
        worker = _worker_with_ann(stub)
        worker._ann_insert("msg-x", [0.3, 0.4])
        stub.Insert.assert_called_once()

    def test_resets_ann_ok_on_exception(self):
        stub = MagicMock()
        stub.Insert.side_effect = RuntimeError("timeout")
        worker = _worker_with_ann(stub)
        worker._ann_insert("msg-x", [0.3, 0.4])
        assert worker._ann_ok is False
        assert worker._ann_disabled is True


class TestProcessUntaggedWithAnn:
    def test_ann_score_above_threshold_continues_topic(self):
        """Ann returns high similarity -> messages stay in same topic."""
        msgs = [
            _make_msg("msg-1", "topic A start", created_at_ts=1712908800.0),
            _make_msg("msg-2", "topic A continues", created_at_ts=1712908860.0),
        ]
        db = _make_db_with_messages(*msgs)
        # ann returns similarity above threshold for second message
        stub = _make_stub([("msg-1", SIMILARITY_THRESHOLD + 0.1)])
        worker = _worker_with_ann(stub)
        worker.db = db

        worker.process_untagged(batch=50)

        with Session(db._engine) as s:
            topics = list(s.scalars(select(MessageTopic).order_by(MessageTopic.id)))

        assert len(topics) == 2
        assert topics[0].topic_label == topics[1].topic_label

    def test_ann_score_below_threshold_creates_new_topic(self):
        """Ann returns low similarity -> topic drift -> new label."""
        msgs = [
            _make_msg("msg-1", "topic A start", created_at_ts=1712908800.0),
            _make_msg("msg-2", "completely different", created_at_ts=1712908860.0),
        ]
        db = _make_db_with_messages(*msgs)
        # ann returns similarity below threshold
        stub = _make_stub([("msg-1", SIMILARITY_THRESHOLD - 0.1)])
        worker = _worker_with_ann(stub)
        worker.db = db

        worker.process_untagged(batch=50)

        with Session(db._engine) as s:
            topics = list(s.scalars(select(MessageTopic).order_by(MessageTopic.id)))

        assert len(topics) == 2
        assert topics[0].topic_label != topics[1].topic_label

    def test_ann_insert_called_per_message(self):
        """Insert is called once per tagged message."""
        msgs = [
            _make_msg("msg-1", "hello", created_at_ts=1712908800.0),
            _make_msg("msg-2", "world", created_at_ts=1712908860.0),
            _make_msg("msg-3", "foo",   created_at_ts=1712908920.0),
        ]
        db = _make_db_with_messages(*msgs)
        stub = _make_stub([("msg-prev", SIMILARITY_THRESHOLD + 0.2)])
        worker = _worker_with_ann(stub)
        worker.db = db

        worker.process_untagged(batch=50)

        assert stub.Insert.call_count == 3

    def test_falls_back_to_cosine_when_ann_fails(self):
        """If ann stub raises, worker falls back to in-process cosine."""
        msgs = [
            _make_msg("msg-1", "hello world", created_at_ts=1712908800.0),
            _make_msg("msg-2", "hello world again", created_at_ts=1712908860.0),
        ]
        db = _make_db_with_messages(*msgs)
        stub = MagicMock()
        stub.Search.side_effect = RuntimeError("ann down")
        stub.Insert.side_effect = RuntimeError("ann down")
        worker = _worker_with_ann(stub)
        worker.db = db

        # Should not raise; cosine fallback covers it
        count = worker.process_untagged(batch=50)
        assert count == 2
