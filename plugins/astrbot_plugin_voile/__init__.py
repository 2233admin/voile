"""XAR-16: AstrBot plugin -- realtime message sink into Voile storage.

Drop into AstrBot plugins/ directory.
Requires: voile core installed (pip install -e /path/to/voile)
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone

# AstrBot plugin contract
PLUGIN_NAME = "voile_sink"
PLUGIN_DESC = "Sink QQ/WeChat messages into Voile storage and push URLs to Redis queue"
PLUGIN_VERSION = "0.1.0"
PLUGIN_AUTHOR = "2233admin"

_URL_RE = re.compile(r"https?://[^\s\u4e00-\u9fff]+")


def info() -> dict:
    return {
        "name": PLUGIN_NAME,
        "description": PLUGIN_DESC,
        "version": PLUGIN_VERSION,
        "author": PLUGIN_AUTHOR,
    }


async def run(event: dict, context: dict) -> None:
    """Called by AstrBot on each incoming message event."""
    from core.schemas import Message, MessageType, Platform
    from core.storage import Database

    db: Database = context.setdefault("voile_db", Database(
        os.environ.get("VOILE_DB_URL", "sqlite:///voile.db")
    ))

    platform_raw = event.get("platform", "qq").lower()
    try:
        platform = Platform(platform_raw)
    except ValueError:
        return  # unsupported platform -- skip silently

    content: str = event.get("raw_message", "") or event.get("content", "")

    msg = Message(
        platform=platform,
        channel_id=str(event.get("group_id") or event.get("channel_id", "dm")),
        user_id=str(event.get("user_id", "unknown")),
        message_id=str(event.get("message_id", "")),
        message_type=MessageType(event.get("message_type", "text")),
        content=content,
        raw_payload=event,
        created_at=datetime.fromtimestamp(
            float(event.get("time", datetime.now(timezone.utc).timestamp())),
            tz=timezone.utc,
        ),
    )

    inserted = db.upsert(msg)

    if inserted and msg.urls:
        _push_urls_to_redis(msg.urls, context)


def _push_urls_to_redis(urls: list[str], context: dict) -> None:
    try:
        import redis

        r: redis.Redis = context.setdefault(
            "voile_redis",
            redis.Redis.from_url(os.environ.get("VOILE_REDIS_URL", "redis://localhost:6379/0")),
        )
        for url in urls:
            r.lpush("voile:url_queue", url)
    except Exception:
        pass  # Redis is best-effort; message already in DB
