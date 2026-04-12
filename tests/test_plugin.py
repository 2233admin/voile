"""Tests for plugins.astrbot_plugin_voile."""
from __future__ import annotations

from core.storage.db import Database
from plugins.astrbot_plugin_voile import info, run

_QQ_EVENT = {
    "platform": "qq",
    "group_id": 12345,
    "user_id": 99999,
    "message_id": "msg-001",
    "message_type": "text",
    "raw_message": "hello world",
    "time": 1712908800,
}


def test_info_shape():
    result = info()
    assert "name" in result
    assert "description" in result
    assert "version" in result
    assert "author" in result


async def test_run_calls_upsert():
    db = Database("sqlite:///:memory:")
    context = {"voile_db": db}
    await run(dict(_QQ_EVENT), context)

    rows = db.recent("12345")
    assert len(rows) == 1
    assert rows[0].message_id == "msg-001"


async def test_run_idempotent():
    db = Database("sqlite:///:memory:")
    context = {"voile_db": db}
    await run(dict(_QQ_EVENT), context)
    await run(dict(_QQ_EVENT), context)

    rows = db.recent("12345")
    assert len(rows) == 1


async def test_run_unsupported_platform_silent():
    db = Database("sqlite:///:memory:")
    context = {"voile_db": db}
    event = dict(_QQ_EVENT, platform="discord", message_id="msg-002")
    await run(event, context)

    rows = db.recent("12345")
    assert len(rows) == 0
