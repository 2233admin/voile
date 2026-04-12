"""Tests for core.agents.link_archiver (XAR-17)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.agents.link_archiver import LinkArchiver
from core.storage.db import Database, LinkRecord


def _make_db() -> Database:
    return Database("sqlite:///:memory:")


def test_archive_with_mock_archiver(monkeypatch):
    db = _make_db()
    archiver = LinkArchiver(db)

    monkeypatch.setattr(archiver, "fetch_metadata", lambda url: {
        "title": "Test Page",
        "summary": "A summary",
        "tags": ["python", "test"],
    })

    result = archiver.archive("https://example.com/page")
    assert result is True

    with Session(db._engine) as s:
        rec = s.scalar(select(LinkRecord).where(LinkRecord.url == "https://example.com/page"))
    assert rec is not None
    assert rec.title == "Test Page"
    assert rec.summary == "A summary"
    assert rec.tags == ["python", "test"]


def test_archive_dedup(monkeypatch):
    db = _make_db()
    archiver = LinkArchiver(db)

    monkeypatch.setattr(archiver, "fetch_metadata", lambda url: {
        "title": "First",
        "summary": "",
        "tags": [],
    })
    archiver.archive("https://example.com/dedup")

    monkeypatch.setattr(archiver, "fetch_metadata", lambda url: {
        "title": "Updated",
        "summary": "new summary",
        "tags": [],
    })
    archiver.archive("https://example.com/dedup")

    with Session(db._engine) as s:
        rows = list(s.scalars(select(LinkRecord).where(LinkRecord.url == "https://example.com/dedup")))
    assert len(rows) == 1
    assert rows[0].title == "Updated"


def test_run_once_empty():
    db = _make_db()
    # Use an unreachable Redis URL so the connection always fails
    archiver = LinkArchiver(db, redis_url="redis://localhost:19999/0")
    result = archiver.run_once()
    assert result == 0
