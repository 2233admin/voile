"""XAR-17: Link archiver agent -- fetches URL metadata and stores to DB."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser

from sqlalchemy import select
from sqlalchemy.orm import Session

from typing import Any

from core.storage.db import Database, LinkRecord


class _TitleParser(HTMLParser):
    """Minimal HTML parser that extracts the <title> text."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


class LinkArchiver:
    def __init__(
        self,
        db: Database,
        archiver_url: str = "http://localhost:8888",
        redis_url: str = "redis://localhost:6379/0",
        obsidian_vault: str | None = None,
    ):
        self.db = db
        self.archiver_url = archiver_url
        self.redis_url = redis_url
        self.obsidian_vault = obsidian_vault

    def fetch_metadata(self, url: str) -> dict[str, Any]:
        """Call Go archiver service. Returns {"title":..,"summary":..} or {"error":..}"""
        try:
            payload = json.dumps({"url": url}).encode()
            req = urllib.request.Request(
                f"{self.archiver_url}/fetch",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())  # type: ignore[no-any-return]
        except Exception:
            pass

        # Fallback: fetch the URL directly and extract <title>
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                charset = "utf-8"
                content_type = resp.headers.get("Content-Type", "")
                if "charset=" in content_type:
                    charset = content_type.split("charset=")[-1].strip()
                html = resp.read(65536).decode(charset, errors="replace")
            parser = _TitleParser()
            parser.feed(html)
            return {"title": parser.title.strip(), "summary": ""}
        except Exception:
            return {"title": "", "summary": ""}

    def archive(self, url: str) -> bool:
        """Fetch + store. Returns True on success."""
        meta = self.fetch_metadata(url)
        title = meta.get("title", "")
        summary = meta.get("summary", "")
        tags = meta.get("tags", [])
        now = datetime.now(tz=UTC)

        with Session(self.db._engine) as s:
            existing = s.scalar(select(LinkRecord).where(LinkRecord.url == url))
            if existing:
                existing.title = title
                existing.summary = summary
                existing.tags = tags
                existing.fetched_at = now
            else:
                s.add(LinkRecord(
                    url=url,
                    title=title,
                    summary=summary,
                    tags=tags,
                    fetched_at=now,
                    obsidian_path=None,
                ))
            s.commit()

        if self.obsidian_vault is not None:
            try:
                from core.obsidian import ObsidianWriter
                ObsidianWriter(self.obsidian_vault).write_link(
                    url=url, title=title, summary=summary, tags=tags
                )
            except Exception:
                pass

        return True

    def run_once(self) -> int:
        """Drain voile:url_queue once. Returns count processed."""
        try:
            import redis
        except ImportError:
            return 0

        try:
            r = redis.from_url(self.redis_url, socket_connect_timeout=2)
            r.ping()
        except Exception:
            return 0

        count = 0
        for _ in range(100):
            item = r.brpop("voile:url_queue", timeout=0.5)
            if item is None:
                break
            _, raw = item  # type: ignore[misc]
            url = raw.decode() if isinstance(raw, bytes) else raw
            self.archive(url)
            count += 1
        return count

    def run_forever(self, sleep: float = 1.0) -> None:
        """Block forever, processing urls."""
        while True:
            self.run_once()
            time.sleep(sleep)
