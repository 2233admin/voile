"""Tests for core.schemas.message (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from core.schemas.message import Message, Platform


def _base_kwargs(**overrides) -> dict:
    kwargs = {
        "platform": "qq",
        "channel_id": "group-1",
        "user_id": "user-1",
        "message_id": "msg-1",
        "content": "hello world",
        "created_at": datetime(2024, 4, 12, tzinfo=timezone.utc),
    }
    kwargs.update(overrides)
    return kwargs


def test_basic_construction():
    msg = Message(**_base_kwargs())
    assert msg.platform == Platform.QQ
    assert msg.channel_id == "group-1"
    assert msg.user_id == "user-1"
    assert msg.message_id == "msg-1"
    assert msg.content == "hello world"
    assert isinstance(msg.created_at, datetime)


def test_auto_extract_urls():
    # Validator fires when urls=[] is explicitly provided (mode="before" skips default_factory).
    msg = Message(**_base_kwargs(
        content="check https://example.com and http://foo.bar/path",
        urls=[],
    ))
    assert "https://example.com" in msg.urls
    assert "http://foo.bar/path" in msg.urls


def test_urls_not_overwritten_when_provided():
    msg = Message(**_base_kwargs(
        content="check https://example.com",
        urls=["https://manual.example.com"],
    ))
    assert msg.urls == ["https://manual.example.com"]
    assert "https://example.com" not in msg.urls


def test_created_at_from_unix_timestamp():
    msg = Message(**_base_kwargs(created_at=1712908800))
    assert isinstance(msg.created_at, datetime)
    assert msg.created_at.tzinfo is not None
    assert msg.created_at == datetime.fromtimestamp(1712908800, tz=timezone.utc)


def test_frozen_raises_on_mutation():
    msg = Message(**_base_kwargs())
    with pytest.raises((ValidationError, TypeError)):
        msg.content = "changed"


def test_invalid_platform_raises():
    with pytest.raises(ValidationError):
        Message(**_base_kwargs(platform="discord"))
