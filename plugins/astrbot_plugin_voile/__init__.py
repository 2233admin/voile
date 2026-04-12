"""XAR-16: AstrBot v3 plugin -- realtime message sink into Voile storage.

Drop into AstrBot's plugins/ directory.
Requires: voile core installed (pip install -e /path/to/voile)
"""
from __future__ import annotations

import os
import re
from datetime import UTC, datetime

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

PLUGIN_VERSION = "0.2.0"

_URL_RE = re.compile(r"https?://[^\s\u4e00-\u9fff]+")

# AstrBot platform name -> voile Platform value
_PLATFORM_MAP = {
    "aiocqhttp": "qq",      # OneBot v11 (NapCatQQ / Lagrange)
    "nakuru": "qq",
    "wechat": "wechat",
    "wecom": "wechat",
}


@register(
    "voile_sink",
    "2233admin",
    "Sink QQ/WeChat messages into Voile storage and push URLs to Redis",
    PLUGIN_VERSION,
)
class VoileSink(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        from core.storage.db import Database

        self._db = Database(os.environ.get("VOILE_DB_URL", "sqlite:///voile.db"))
        self._redis_url = os.environ.get("VOILE_REDIS_URL", "redis://localhost:6379/0")
        self._redis = None  # lazy

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    @filter.all()
    async def on_message(self, event: AstrMessageEvent) -> None:
        from core.schemas.message import Message, Platform

        # Platform detection
        adapter = getattr(event, "platform_meta", None)
        adapter_name = (adapter.name if adapter else "").lower()
        platform_val = _PLATFORM_MAP.get(adapter_name, "qq")
        try:
            platform = Platform(platform_val)
        except ValueError:
            return

        content: str = event.message_str or ""
        sender_id = str(event.get_sender_id() or "unknown")
        # session_id encodes channel: group_xxxx for groups, friend_xxxx for DMs
        channel_id = str(getattr(event, "session_id", None) or "unknown")
        msg_id = str(getattr(event, "message_id", None) or "")
        ts = getattr(event, "timestamp", None)
        created_at = (
            datetime.fromtimestamp(float(ts), tz=UTC) if ts
            else datetime.now(UTC)
        )

        urls = _URL_RE.findall(content)

        msg = Message(
            platform=platform,
            channel_id=channel_id,
            user_id=sender_id,
            message_id=msg_id,
            content=content,
            urls=urls or None,
            created_at=created_at,
        )

        inserted = self._db.upsert(msg)

        if inserted and urls:
            self._push_urls(urls)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _push_urls(self, urls: list[str]) -> None:
        try:
            import redis

            if self._redis is None:
                self._redis = redis.Redis.from_url(self._redis_url)
            for url in urls:
                self._redis.lpush("voile:url_queue", url)
        except Exception:
            pass  # Redis is best-effort; message already in DB
