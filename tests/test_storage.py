"""Tests for core.storage.db (SQLite in-memory)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.schemas.message import Message, Platform
from core.storage.db import Database


def _make_msg(message_id: str = "msg-1", content: str = "hello", created_at_ts: float = 1712908800.0) -> Message:
    return Message(
        platform=Platform.QQ,
        channel_id="group-1",
        user_id="user-1",
        message_id=message_id,
        content=content,
        created_at=datetime.fromtimestamp(created_at_ts, tz=timezone.utc),
    )


def test_upsert_new_returns_true():
    db = Database("sqlite:///:memory:")
    assert db.upsert(_make_msg()) is True


def test_upsert_duplicate_returns_false():
    db = Database("sqlite:///:memory:")
    msg = _make_msg()
    assert db.upsert(msg) is True
    assert db.upsert(msg) is False


def test_recent_returns_descending_order():
    db = Database("sqlite:///:memory:")
    db.upsert(_make_msg("msg-1", created_at_ts=1712908800.0))
    db.upsert(_make_msg("msg-2", created_at_ts=1712908900.0))
    db.upsert(_make_msg("msg-3", created_at_ts=1712909000.0))

    rows = db.recent("group-1")
    assert len(rows) == 3
    assert rows[0].message_id == "msg-3"
    assert rows[1].message_id == "msg-2"
    assert rows[2].message_id == "msg-1"


def test_recent_limit():
    db = Database("sqlite:///:memory:")
    db.upsert(_make_msg("msg-1", created_at_ts=1712908800.0))
    db.upsert(_make_msg("msg-2", created_at_ts=1712908900.0))

    rows = db.recent("group-1", limit=1)
    assert len(rows) == 1
    assert rows[0].message_id == "msg-2"
