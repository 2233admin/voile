"""Tests for core.agents.decision_tracker (XAR-21)."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from core.agents.decision_tracker import (
    DecisionTracker,
    detect_decision_segment,
)
from core.schemas.message import Message, Platform
from core.storage.db import Database, MessageRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    message_id: str,
    content: str,
    user_id: str = "user-1",
    channel_id: str = "ch-1",
    ts: float = 1712908800.0,
) -> MessageRecord:
    """Build a detached MessageRecord without a DB session."""
    rec = MessageRecord()
    rec.id = 0
    rec.platform = "qq"
    rec.channel_id = channel_id
    rec.user_id = user_id
    rec.message_id = message_id
    rec.message_type = "text"
    rec.content = content
    rec.raw_payload = {}
    rec.created_at = datetime.fromtimestamp(ts, tz=UTC)
    rec.urls = []
    return rec


def _make_msg(
    message_id: str,
    content: str,
    channel_id: str = "ch-1",
    user_id: str = "user-1",
    ts: float = 1712908800.0,
) -> Message:
    return Message(
        platform=Platform.QQ,
        channel_id=channel_id,
        user_id=user_id,
        message_id=message_id,
        content=content,
        created_at=datetime.fromtimestamp(ts, tz=UTC),
    )


def _db_with(*messages: Message) -> Database:
    db = Database("sqlite:///:memory:")
    for m in messages:
        db.upsert(m)
    return db


# ---------------------------------------------------------------------------
# Test 1: no decision in messages without proposal+conclusion pair
# ---------------------------------------------------------------------------

def test_no_decision_without_conclusion():
    """Messages with only proposals but no conclusion keywords → empty result."""
    msgs = [
        _make_record("m1", "我建议我们改用新框架", ts=1_000.0),
        _make_record("m2", "要不要试试看", ts=1_001.0),
        _make_record("m3", "大家怎么看？同意吗", ts=1_002.0),
    ]
    result = detect_decision_segment(msgs)
    assert result == []


def test_no_decision_without_proposal():
    """Messages with only conclusion keywords but no proposal → empty result."""
    msgs = [
        _make_record("m1", "我觉得不错", ts=1_000.0),
        _make_record("m2", "好的，就这样，定了", ts=1_001.0),
    ]
    result = detect_decision_segment(msgs)
    assert result == []


# ---------------------------------------------------------------------------
# Test 2: clear proposal+conclusion in same window → one decision detected
# ---------------------------------------------------------------------------

def test_detects_single_decision():
    """A clear proposal followed by a conclusion within 20 messages is detected."""
    msgs = [
        _make_record("m1", "我建议我们把发布时间推迟一周", user_id="alice", ts=1_000.0),
        _make_record("m2", "同意，时间确实紧", user_id="bob", ts=1_001.0),
        _make_record("m3", "但是要通知客户", user_id="carol", ts=1_002.0),
        _make_record("m4", "好的，就这样，定了，推迟一周", user_id="alice", ts=1_003.0),
    ]
    result = detect_decision_segment(msgs)
    assert len(result) == 1
    seg = result[0]
    assert seg["title"]           # non-empty
    assert "推迟" in seg["proposal"] or "建议" in seg["proposal"]
    assert "定了" in seg["conclusion"] or "就这样" in seg["conclusion"]
    assert seg["discussion_count"] >= 1
    assert set(seg["participants"]) == {"alice", "bob", "carol"}
    assert len(seg["message_ids"]) == 4
    assert seg["start_at"] < seg["end_at"]


# ---------------------------------------------------------------------------
# Test 3: window boundary — proposal and conclusion more than 20 msgs apart
# ---------------------------------------------------------------------------

def test_window_boundary_no_match():
    """Proposal and conclusion separated by >20 messages are NOT detected."""
    msgs = []
    msgs.append(_make_record("m0", "提议：我们应该重写后端", ts=1_000.0))
    for i in range(1, 21):
        msgs.append(_make_record(f"m{i}", f"闲聊消息{i}", ts=1_000.0 + i))
    # conclusion is now at index 21, more than 20 away from proposal at index 0
    msgs.append(_make_record("m21", "好的，定了，大家散了", ts=1_022.0))

    result = detect_decision_segment(msgs)
    # The proposal window (indices 0-19) contains no conclusion.
    # The conclusion window (indices 2-21) contains no proposal keyword.
    assert result == []


# ---------------------------------------------------------------------------
# Test 4: multiple participants extracted correctly
# ---------------------------------------------------------------------------

def test_participants_are_unique():
    """Each unique user_id appears exactly once in participants list."""
    msgs = [
        _make_record("m1", "建议改为双周发布", user_id="u1", ts=1_000.0),
        _make_record("m2", "同意", user_id="u2", ts=1_001.0),
        _make_record("m2b", "支持", user_id="u2", ts=1_001.5),  # u2 again
        _make_record("m3", "不同意，风险太大", user_id="u3", ts=1_002.0),
        _make_record("m4", "确定，双周发布", user_id="u1", ts=1_003.0),
    ]
    result = detect_decision_segment(msgs)
    assert len(result) >= 1
    participants = result[0]["participants"]
    assert len(participants) == len(set(participants)), "participants must be unique"
    assert set(participants) == {"u1", "u2", "u3"}


# ---------------------------------------------------------------------------
# Test 5: run_once writes decisions via ObsidianWriter
# ---------------------------------------------------------------------------

def test_run_once_calls_obsidian_writer(tmp_path: Path):
    """run_once should call writer.write_decision for each detected decision."""
    fake_messages = [
        _make_record("m1", "建议我们把下次例会改到周五", ts=1_712_908_800.0),
        _make_record("m2", "同意，周五更方便", ts=1_712_908_860.0),
        _make_record("m3", "好的，就这样，定了", ts=1_712_908_920.0),
    ]

    tracker = DecisionTracker(
        Database("sqlite:///:memory:"),
        channel_id="ch-1",
        obsidian_vault=str(tmp_path),
    )
    # Bypass the date-window query by mocking _fetch_recent_messages directly
    tracker._fetch_recent_messages = lambda days=7: fake_messages  # type: ignore[method-assign]

    decisions = tracker.run_once()

    # At least one decision should have been detected and written
    assert len(decisions) >= 1

    # Obsidian decisions/ dir should have a markdown file
    decision_files = list((tmp_path / "decisions").glob("*.md"))
    assert len(decision_files) >= 1

    content = decision_files[0].read_text(encoding="utf-8")
    assert "## Conclusion" in content
    assert "## Discussion" in content


# ---------------------------------------------------------------------------
# Test 6: run_once returns empty list when no decisions in messages
# ---------------------------------------------------------------------------

def test_run_once_no_decisions(tmp_path: Path):
    """run_once returns [] and writes nothing when no decision is detected."""
    db = _db_with(
        _make_msg("m1", "今天天气真好", ts=1_712_908_800.0),
        _make_msg("m2", "是啊，适合出去走走", ts=1_712_908_860.0),
    )

    tracker = DecisionTracker(
        db,
        channel_id="ch-1",
        obsidian_vault=str(tmp_path),
    )

    decisions = tracker.run_once()
    assert decisions == []
    assert not (tmp_path / "decisions").exists()


# ---------------------------------------------------------------------------
# Test 7: detect_decision_segment discussion_count accuracy
# ---------------------------------------------------------------------------

def test_discussion_count():
    """discussion_count reflects messages containing DISCUSSION_KW."""
    msgs = [
        _make_record("m1", "提议：统一代码风格用black", ts=1_000.0),
        _make_record("m2", "同意，规范统一好", ts=1_001.0),
        _make_record("m3", "反对，不喜欢强制格式化", ts=1_002.0),
        _make_record("m4", "但是一致性很重要", ts=1_003.0),
        _make_record("m5", "好，定了，用black", ts=1_004.0),
    ]
    result = detect_decision_segment(msgs)
    assert len(result) == 1
    # m2 (同意), m3 (反对), m4 (但是) all match DISCUSSION_KW
    assert result[0]["discussion_count"] == 3


# ---------------------------------------------------------------------------
# Test 8: message_ids list is correct
# ---------------------------------------------------------------------------

def test_message_ids_in_segment():
    """message_ids should list every message_id in the detected window."""
    msgs = [
        _make_record("alpha", "能不能下周启动新项目", ts=1_000.0),
        _make_record("beta", "支持", ts=1_001.0),
        _make_record("gamma", "确定，下周启动", ts=1_002.0),
    ]
    result = detect_decision_segment(msgs)
    assert len(result) == 1
    assert result[0]["message_ids"] == ["alpha", "beta", "gamma"]
