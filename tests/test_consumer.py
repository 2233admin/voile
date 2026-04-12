"""Tests for core.ingest.consumer -- _parse_wechat()."""
from __future__ import annotations

from datetime import UTC, datetime

from core.ingest.consumer import RedisConsumer, _parse_wechat
from core.schemas import MessageType, Platform
from core.storage.db import Database


def _noop_cleaner(text: str) -> tuple[str, list[str]]:
    return text, []


def _empty_cleaner(text: str) -> tuple[str, list[str]]:
    return "", []


def test_parse_wechat_text():
    event = {
        "id": "msg_001",
        "from_user": "user123",
        "to_user": "group456",
        "content": "hello world",
        "create_time": 1712345678,
        "msg_type": "text",
    }
    msg = _parse_wechat(event, _noop_cleaner)
    assert msg is not None
    assert msg.platform == Platform.WECHAT
    assert msg.channel_id == "group456"
    assert msg.user_id == "user123"
    assert msg.message_id == "msg_001"
    assert msg.message_type == MessageType.TEXT
    assert msg.content == "hello world"
    assert msg.created_at == datetime.fromtimestamp(1712345678, tz=UTC)


def test_parse_wechat_image():
    event = {
        "id": "msg_002",
        "from_user": "user123",
        "to_user": "group456",
        "content": "[image data]",
        "create_time": 1712345700,
        "msg_type": "image",
    }
    msg = _parse_wechat(event, _noop_cleaner)
    assert msg is not None
    assert msg.message_type == MessageType.IMAGE


def test_parse_wechat_empty_content_returns_none():
    event = {
        "id": "msg_003",
        "from_user": "user123",
        "to_user": "group456",
        "content": "some text",
        "create_time": 1712345800,
        "msg_type": "text",
    }
    msg = _parse_wechat(event, _empty_cleaner)
    assert msg is None


def test_parse_wechat_group_id_fallback():
    event = {
        "id": "msg_004",
        "from_user": "user999",
        "group_id": "grp789",
        "content": "batch message",
        "create_time": 1712345900,
        "msg_type": "text",
    }
    msg = _parse_wechat(event, _noop_cleaner)
    assert msg is not None
    assert msg.channel_id == "grp789"


def test_parse_wechat_no_channel_defaults_dm():
    event = {
        "id": "msg_005",
        "from_user": "user111",
        "content": "direct message",
        "create_time": 1712346000,
        "msg_type": "text",
    }
    msg = _parse_wechat(event, _noop_cleaner)
    assert msg is not None
    assert msg.channel_id == "dm"


def test_parse_wechat_unknown_msg_type():
    event = {
        "id": "msg_006",
        "from_user": "user222",
        "to_user": "group456",
        "content": "some link",
        "create_time": 1712346100,
        "msg_type": "link",
    }
    msg = _parse_wechat(event, _noop_cleaner)
    assert msg is not None
    assert msg.message_type == MessageType.UNKNOWN


class TestCleanerInit:
    def _make_consumer(self) -> RedisConsumer:
        db = Database("sqlite:///:memory:")
        return RedisConsumer(db, cleaner_addr="localhost:50051")

    def test_disabled_after_import_failure(self):
        """If grpc import fails, _cleaner_disabled is set and init is not retried."""
        consumer = self._make_consumer()
        assert not consumer._cleaner_disabled
        # grpc likely available, but simulate import failure via flag
        consumer._cleaner_disabled = True
        consumer._init_cleaner()  # must return early without touching _cleaner_ok
        assert not consumer._cleaner_ok

    def test_no_init_when_addr_is_none(self):
        db = Database("sqlite:///:memory:")
        consumer = RedisConsumer(db, cleaner_addr=None)
        consumer._init_cleaner()
        assert not consumer._cleaner_ok
        assert not consumer._cleaner_disabled

    def test_clean_falls_back_when_disabled(self):
        consumer = self._make_consumer()
        consumer._cleaner_disabled = True
        text, urls = consumer._clean("hello world")
        assert text == "hello world"
        assert urls == []
