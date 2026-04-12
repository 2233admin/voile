"""XAR-12: Universal cross-platform message schema (Pydantic v2)."""
from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

_URL_RE = re.compile(r"https?://[^\s\u4e00-\u9fff]+")


class Platform(StrEnum):
    QQ = "qq"
    WECHAT = "wechat"


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    LOCATION = "location"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class Message(BaseModel):
    """Normalized message -- the single data contract across the entire system.

    All platform adapters (QQ/WeChat) MUST produce this shape before writing to storage.
    Downstream workers (topic/sentiment/persona) consume ONLY this shape.
    """

    platform: Platform
    channel_id: str = Field(..., description="Group or chat room ID on the source platform")
    user_id: str = Field(..., description="Sender ID on the source platform")
    message_id: str = Field(..., description="Platform-native dedup key")
    message_type: MessageType = MessageType.TEXT
    content: str = Field(..., description="Normalized UTF-8 text content")
    raw_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Original platform JSON -- for forensics only, do not rely on structure",
    )
    created_at: datetime = Field(..., description="Message timestamp (UTC, timezone-aware)")
    urls: list[str] = Field(default_factory=list, description="URLs extracted from content")

    model_config = {"frozen": True}

    @field_validator("urls", mode="before")
    @classmethod
    def auto_extract_urls(cls, v: list[str], info: Any) -> list[str]:
        """If urls not provided, extract from content automatically."""
        if v:
            return v
        content = (info.data or {}).get("content", "")
        return _URL_RE.findall(content)

    @field_validator("created_at", mode="before")
    @classmethod
    def ensure_utc(cls, v: Any) -> datetime:
        if isinstance(v, int | float):
            from datetime import timezone
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v
