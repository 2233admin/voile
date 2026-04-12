"""XAR-22: Redis consumer -- reads voile:raw_queue, normalizes, writes to DB."""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from core.schemas import Message, MessageType, Platform
from core.storage.db import Database

logger = logging.getLogger(__name__)

QUEUE_KEY = "voile:raw_queue"
URL_QUEUE_KEY = "voile:url_queue"


def _parse_onebot(event: dict[str, Any], cleaner_fn: Any) -> Message | None:
    """Parse a QQ OneBot v11 event. Returns None if not a message event."""
    if event.get("post_type") != "message":
        return None

    group_id = event.get("group_id")
    channel_id = str(group_id) if group_id else str(event.get("user_id", "dm"))

    raw_content: str = event.get("raw_message", "") or event.get("content", "")
    content, urls = cleaner_fn(raw_content)

    try:
        msg_type = MessageType(event.get("message_type", "text"))
    except ValueError:
        msg_type = MessageType.UNKNOWN

    return Message(
        platform=Platform.QQ,
        channel_id=channel_id,
        user_id=str(event.get("user_id", "unknown")),
        message_id=str(event.get("message_id", "")),
        message_type=msg_type,
        content=content,
        urls=urls,
        raw_payload=event,
        created_at=datetime.fromtimestamp(
            float(event.get("time", datetime.now(UTC).timestamp())), tz=UTC
        ),
    )


class RedisConsumer:
    """Reads voile:raw_queue and writes to DB. Optionally applies Rust cleaner."""

    def __init__(
        self,
        db: Database,
        redis_url: str = "redis://localhost:6379/0",
        cleaner_addr: str | None = "localhost:50051",
    ) -> None:
        self.db = db
        self.redis_url = redis_url
        self.cleaner_addr = cleaner_addr
        self._stub: Any = None
        self._pb2: Any = None
        self._cleaner_ok = False

    def _init_cleaner(self) -> None:
        if self._cleaner_ok or self.cleaner_addr is None:
            return
        try:
            import grpc
            from core.gen import voile_pb2, voile_pb2_grpc

            channel = grpc.insecure_channel(self.cleaner_addr)
            self._stub = voile_pb2_grpc.TextCleanerStub(channel)
            self._pb2 = voile_pb2
            self._cleaner_ok = True
            logger.info("cleaner connected at %s", self.cleaner_addr)
        except Exception as exc:
            logger.debug("cleaner unavailable (%s), using regex fallback", exc)

    def _clean(self, text: str) -> tuple[str, list[str]]:
        """Returns (cleaned_text, urls). Tries Rust cleaner, falls back to identity."""
        self._init_cleaner()
        if self._cleaner_ok and self._stub is not None:
            try:
                resp = self._stub.Clean(
                    self._pb2.CleanRequest(text=text, extract_urls=True)
                )
                return resp.cleaned_text, list(resp.extracted_urls)
            except Exception as exc:
                logger.warning("cleaner call failed: %s", exc)
                self._cleaner_ok = False  # retry init next batch
        # Identity fallback — Message schema extracts URLs via regex
        return text, []

    def _handle(self, raw: bytes, r: Any) -> None:
        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        try:
            data = json.loads(raw_str)
        except json.JSONDecodeError:
            logger.warning("invalid JSON in queue, skipping")
            return

        events: list[dict[str, Any]] = data if isinstance(data, list) else [data]

        for event in events:
            msg = _parse_onebot(event, self._clean)
            if msg is None:
                continue
            if self.db.upsert(msg):
                for url in msg.urls:
                    r.lpush(URL_QUEUE_KEY, url)
                logger.debug("stored msg %s channel %s", msg.message_id, msg.channel_id)

    def run_once(self) -> int:
        try:
            import redis as redis_lib
        except ImportError:
            return 0

        try:
            r = redis_lib.from_url(self.redis_url, socket_connect_timeout=2)
            r.ping()
        except Exception:
            return 0

        count = 0
        for _ in range(200):
            item = r.brpop(QUEUE_KEY, timeout=0.5)
            if item is None:
                break
            _, raw = item  # type: ignore[misc]
            self._handle(raw, r)
            count += 1
        return count

    def run_forever(self, sleep: float = 0.5) -> None:
        while True:
            self.run_once()
            time.sleep(sleep)
