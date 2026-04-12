"""Tests for core.query -- all public functions, in-memory SQLite."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from core.query import (
    archived_links,
    channel_stats,
    find_decisions,
    list_channels,
    recent_messages,
    sentiment_summary,
    topic_summary,
)
from core.schemas.message import Platform
from core.storage.db import (
    Database,
    LinkRecord,
    MessageRecord,
    MessageSentiment,
    MessageTopic,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2026, 4, 10, 12, 0, 0, tzinfo=UTC)  # within any 7-day window


def _db() -> Database:
    return Database("sqlite:///:memory:")


def _msg(
    message_id: str,
    content: str,
    channel_id: str = "ch-1",
    user_id: str = "user-1",
    offset_seconds: int = 0,
) -> MessageRecord:
    return MessageRecord(
        platform=Platform.QQ,
        channel_id=channel_id,
        user_id=user_id,
        message_id=message_id,
        message_type="text",
        content=content,
        raw_payload={},
        created_at=_BASE_TS + timedelta(seconds=offset_seconds),
        urls=[],
    )


def _seed_messages(db: Database, records: list[MessageRecord]) -> None:
    with Session(db._engine) as s:
        s.add_all(records)
        s.commit()


def _seed_topics(db: Database, records: list[MessageTopic]) -> None:
    with Session(db._engine) as s:
        s.add_all(records)
        s.commit()


def _seed_sentiments(db: Database, records: list[MessageSentiment]) -> None:
    with Session(db._engine) as s:
        s.add_all(records)
        s.commit()


def _seed_links(db: Database, records: list[LinkRecord]) -> None:
    with Session(db._engine) as s:
        s.add_all(records)
        s.commit()


# ---------------------------------------------------------------------------
# recent_messages
# ---------------------------------------------------------------------------


def test_recent_messages_normal():
    db = _db()
    _seed_messages(db, [
        _msg("m1", "hello", offset_seconds=0),
        _msg("m2", "world", offset_seconds=10),
    ])
    result = recent_messages(db, "ch-1")
    assert "user-1: hello" in result
    assert "user-1: world" in result
    # reversed display: earlier message first in output
    assert result.index("hello") < result.index("world")


def test_recent_messages_empty():
    db = _db()
    result = recent_messages(db, "ch-nobody")
    assert "No messages found" in result


def test_recent_messages_limit():
    db = _db()
    _seed_messages(db, [_msg(f"m{i}", f"msg{i}", offset_seconds=i) for i in range(10)])
    result = recent_messages(db, "ch-1", limit=3)
    # Only 3 lines of content
    lines = [l for l in result.splitlines() if "user-1:" in l]
    assert len(lines) == 3


def test_recent_messages_channel_isolation():
    db = _db()
    _seed_messages(db, [
        _msg("m1", "in-ch1", channel_id="ch-1"),
        _msg("m2", "in-ch2", channel_id="ch-2"),
    ])
    result = recent_messages(db, "ch-1")
    assert "in-ch1" in result
    assert "in-ch2" not in result


# ---------------------------------------------------------------------------
# topic_summary
# ---------------------------------------------------------------------------


def test_topic_summary_normal():
    db = _db()
    _seed_topics(db, [
        MessageTopic(message_id="m1", channel_id="ch-1", topic_label="AI",
                     segment_start="m1", similarity_score=0.9, created_at=_BASE_TS),
        MessageTopic(message_id="m2", channel_id="ch-1", topic_label="AI",
                     segment_start="m1", similarity_score=0.8, created_at=_BASE_TS),
        MessageTopic(message_id="m3", channel_id="ch-1", topic_label="Gaming",
                     segment_start="m3", similarity_score=0.7, created_at=_BASE_TS),
    ])
    result = topic_summary(db, "ch-1")
    assert "AI" in result
    assert "Gaming" in result
    # AI has count 2, should appear before Gaming
    assert result.index("AI") < result.index("Gaming")


def test_topic_summary_empty():
    db = _db()
    result = topic_summary(db, "ch-nobody")
    assert "No topic data" in result


def test_topic_summary_old_data_excluded():
    """Topics older than the requested window should not appear."""
    db = _db()
    old_ts = _BASE_TS - timedelta(days=30)
    _seed_topics(db, [
        MessageTopic(message_id="m1", channel_id="ch-1", topic_label="OldTopic",
                     segment_start="m1", similarity_score=0.5, created_at=old_ts),
    ])
    result = topic_summary(db, "ch-1", days=7)
    assert "No topic data" in result


# ---------------------------------------------------------------------------
# sentiment_summary
# ---------------------------------------------------------------------------


def test_sentiment_summary_normal():
    db = _db()
    _seed_messages(db, [
        _msg("m1", "great", offset_seconds=0),
        _msg("m2", "ok", offset_seconds=1),
        _msg("m3", "bad", offset_seconds=2),
    ])
    _seed_sentiments(db, [
        MessageSentiment(message_id="m1", label="positive", score=0.9, created_at=_BASE_TS),
        MessageSentiment(message_id="m2", label="neutral", score=0.6, created_at=_BASE_TS),
        MessageSentiment(message_id="m3", label="negative", score=0.8, created_at=_BASE_TS),
    ])
    result = sentiment_summary(db, "ch-1")
    assert "positive" in result
    assert "neutral" in result
    assert "negative" in result
    assert "3 labelled" in result


def test_sentiment_summary_no_messages():
    db = _db()
    result = sentiment_summary(db, "ch-nobody")
    assert "No messages" in result


def test_sentiment_summary_messages_but_no_sentiments():
    db = _db()
    _seed_messages(db, [_msg("m1", "hello")])
    result = sentiment_summary(db, "ch-1")
    assert "No sentiment data" in result


def test_sentiment_summary_percentage():
    db = _db()
    _seed_messages(db, [_msg(f"m{i}", "x", offset_seconds=i) for i in range(4)])
    _seed_sentiments(db, [
        MessageSentiment(message_id="m0", label="positive", score=0.9, created_at=_BASE_TS),
        MessageSentiment(message_id="m1", label="positive", score=0.9, created_at=_BASE_TS),
        MessageSentiment(message_id="m2", label="positive", score=0.9, created_at=_BASE_TS),
        MessageSentiment(message_id="m3", label="negative", score=0.7, created_at=_BASE_TS),
    ])
    result = sentiment_summary(db, "ch-1")
    # 3 positive out of 4 = 75.0%
    assert "75.0%" in result


# ---------------------------------------------------------------------------
# archived_links
# ---------------------------------------------------------------------------


def test_archived_links_normal():
    db = _db()
    _seed_links(db, [
        LinkRecord(url="https://example.com/a", title="Article A",
                   summary="Summary A", tags=["tech"], fetched_at=_BASE_TS),
        LinkRecord(url="https://example.com/b", title="Article B",
                   summary="Summary B", tags=["news"], fetched_at=_BASE_TS),
    ])
    result = archived_links(db)
    assert "Article A" in result
    assert "Article B" in result


def test_archived_links_empty():
    db = _db()
    result = archived_links(db)
    assert "No archived links found" in result


def test_archived_links_keyword_filter_match():
    db = _db()
    _seed_links(db, [
        LinkRecord(url="https://a.com", title="Python Tutorial",
                   summary="Learn python", tags=[], fetched_at=_BASE_TS),
        LinkRecord(url="https://b.com", title="JavaScript Guide",
                   summary="JS stuff", tags=[], fetched_at=_BASE_TS),
    ])
    result = archived_links(db, keyword="python")
    assert "Python Tutorial" in result
    assert "JavaScript Guide" not in result


def test_archived_links_keyword_no_match():
    db = _db()
    _seed_links(db, [
        LinkRecord(url="https://a.com", title="Rust book",
                   summary="systems", tags=[], fetched_at=_BASE_TS),
    ])
    result = archived_links(db, keyword="haskell")
    assert "No archived links found" in result
    assert "haskell" in result


def test_archived_links_tag_filter():
    db = _db()
    _seed_links(db, [
        LinkRecord(url="https://c.com", title="Tagged Post",
                   summary="some content", tags=["quant", "finance"], fetched_at=_BASE_TS),
    ])
    result = archived_links(db, keyword="quant")
    assert "Tagged Post" in result


# ---------------------------------------------------------------------------
# find_decisions
# ---------------------------------------------------------------------------


def _decision_messages(channel_id: str = "ch-1") -> list[MessageRecord]:
    """A minimal sequence that triggers detect_decision_segment:
    one PROPOSAL_KW + one CONCLUSION_KW in the same 20-message window."""
    return [
        _msg("d1", "建议我们换一个方案", channel_id=channel_id,
             user_id="alice", offset_seconds=0),
        _msg("d2", "同意，这样更好", channel_id=channel_id,
             user_id="bob", offset_seconds=10),
        _msg("d3", "好的就这样决定了", channel_id=channel_id,
             user_id="alice", offset_seconds=20),
    ]


def test_find_decisions_normal():
    db = _db()
    _seed_messages(db, _decision_messages())
    result = find_decisions(db, "ch-1")
    assert "found" in result or "Decisions" in result
    assert "alice" in result or "bob" in result


def test_find_decisions_empty_channel():
    db = _db()
    result = find_decisions(db, "ch-nobody")
    assert "No decision segments" in result


def test_find_decisions_no_keywords():
    """Messages without decision keywords should yield no segments."""
    db = _db()
    _seed_messages(db, [
        _msg("n1", "今天天气真好", offset_seconds=0),
        _msg("n2", "是啊，出去玩吧", offset_seconds=10),
    ])
    result = find_decisions(db, "ch-1")
    assert "No decision segments" in result


def test_find_decisions_includes_conclusion():
    db = _db()
    _seed_messages(db, _decision_messages())
    result = find_decisions(db, "ch-1")
    # conclusion text should appear (拍板/决定/就这样...)
    assert "决定" in result or "conclusion" in result


# ---------------------------------------------------------------------------
# channel_stats
# ---------------------------------------------------------------------------


def test_channel_stats_normal():
    db = _db()
    _seed_messages(db, [
        _msg("s1", "hi", user_id="alice", offset_seconds=0),
        _msg("s2", "hey", user_id="bob", offset_seconds=1),
        _msg("s3", "yo", user_id="alice", offset_seconds=2),
    ])
    result = channel_stats(db, "ch-1")
    assert "3 messages" in result
    assert "2 active users" in result


def test_channel_stats_empty():
    db = _db()
    result = channel_stats(db, "ch-nobody")
    assert "0 messages" in result
    assert "0 active users" in result


def test_channel_stats_channel_id_in_output():
    db = _db()
    _seed_messages(db, [_msg("x1", "test")])
    result = channel_stats(db, "ch-1")
    assert "ch-1" in result


# ---------------------------------------------------------------------------
# list_channels
# ---------------------------------------------------------------------------


def test_list_channels_normal():
    db = _db()
    _seed_messages(db, [
        _msg("c1", "msg", channel_id="alpha"),
        _msg("c2", "msg", channel_id="alpha"),
        _msg("c3", "msg", channel_id="beta"),
    ])
    result = list_channels(db)
    assert "alpha" in result
    assert "beta" in result
    # alpha has 2 messages, should appear before beta
    assert result.index("alpha") < result.index("beta")


def test_list_channels_empty():
    db = _db()
    result = list_channels(db)
    assert "No channels" in result


def test_list_channels_message_counts():
    db = _db()
    _seed_messages(db, [
        _msg("v1", "a", channel_id="solo"),
    ])
    result = list_channels(db)
    assert "1 messages" in result
