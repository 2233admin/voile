"""Voile query helpers -- structured read access to all DB tables."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.agents.decision_tracker import detect_decision_segment
from core.storage.db import Database, LinkRecord, MessageRecord, MessageSentiment, MessageTopic


def recent_messages(db: Database, channel_id: str, limit: int = 50) -> str:
    records = db.recent(channel_id, limit)
    if not records:
        return f"No messages found for channel {channel_id}"
    lines = []
    for r in reversed(records):
        ts = r.created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(f"[{ts}] {r.user_id}: {r.content}")
    return "\n".join(lines)


def topic_summary(db: Database, channel_id: str, days: int = 7) -> str:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with Session(db._engine) as s:
        rows = list(s.scalars(
            select(MessageTopic)
            .where(MessageTopic.channel_id == channel_id)
            .where(MessageTopic.created_at >= cutoff)
            .order_by(MessageTopic.created_at.desc())
            .limit(200)
        ))
    if not rows:
        return f"No topic data for channel {channel_id} in last {days} days"
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.topic_label] = counts.get(r.topic_label, 0) + 1
    sorted_topics = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    lines = [f"Topics in #{channel_id} (last {days}d):"]
    for label, count in sorted_topics[:15]:
        lines.append(f"  {count:3d}x  {label}")
    return "\n".join(lines)


def sentiment_summary(db: Database, channel_id: str, days: int = 7) -> str:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with Session(db._engine) as s:
        msg_ids = list(s.scalars(
            select(MessageRecord.message_id)
            .where(MessageRecord.channel_id == channel_id)
            .where(MessageRecord.created_at >= cutoff)
        ))
        if not msg_ids:
            return f"No messages for channel {channel_id} in last {days} days"
        sentiments = list(s.scalars(
            select(MessageSentiment).where(MessageSentiment.message_id.in_(msg_ids))
        ))
    if not sentiments:
        return f"No sentiment data yet for channel {channel_id}"
    counts: dict[str, int] = {}
    for row in sentiments:
        counts[row.label] = counts.get(row.label, 0) + 1
    total = len(sentiments)
    lines = [f"Sentiment in #{channel_id} (last {days}d, {total} labelled):"]
    for label in ("positive", "neutral", "negative"):
        n = counts.get(label, 0)
        pct = 100 * n / total if total else 0
        lines.append(f"  {label:10s}: {n:4d}  ({pct:.1f}%)")
    return "\n".join(lines)


def archived_links(db: Database, keyword: str | None = None, limit: int = 20) -> str:
    with Session(db._engine) as s:
        rows = list(s.scalars(
            select(LinkRecord).order_by(LinkRecord.fetched_at.desc()).limit(limit * 4)
        ))
    if keyword:
        kw = keyword.lower()
        rows = [
            r for r in rows
            if kw in r.title.lower()
            or kw in r.summary.lower()
            or any(kw in t.lower() for t in r.tags)
        ]
    rows = rows[:limit]
    if not rows:
        return "No archived links found" + (f" matching {keyword!r}" if keyword else "")
    label = f" matching {keyword!r}" if keyword else ""
    lines = [f"Archived links{label} ({len(rows)}):"]
    for r in rows:
        ts = r.fetched_at.strftime("%Y-%m-%d")
        lines.append(f"  [{ts}] {r.title or r.url}")
        if r.tags:
            lines.append(f"    tags: {', '.join(r.tags)}")
        if r.summary:
            lines.append(f"    {r.summary[:120]}")
    return "\n".join(lines)


def find_decisions(db: Database, channel_id: str, days: int = 7) -> str:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with Session(db._engine) as s:
        messages = list(s.scalars(
            select(MessageRecord)
            .where(MessageRecord.channel_id == channel_id)
            .where(MessageRecord.created_at >= cutoff)
            .order_by(MessageRecord.created_at.asc())
        ))
    decisions = detect_decision_segment(messages)
    if not decisions:
        return f"No decision segments detected in #{channel_id} (last {days} days)"
    lines = [f"Decisions in #{channel_id} (last {days}d, {len(decisions)} found):"]
    for i, d in enumerate(decisions, 1):
        lines.append(f"\n[{i}] {d['title']}")
        lines.append(f"    participants : {', '.join(d['participants'])}")
        lines.append(f"    discussion   : {d['discussion_count']} messages")
        if d["conclusion"]:
            lines.append(f"    conclusion   : {d['conclusion'][:120]}")
    return "\n".join(lines)


def channel_stats(db: Database, channel_id: str, days: int = 7) -> str:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with Session(db._engine) as s:
        total = s.scalar(
            select(func.count()).select_from(MessageRecord)
            .where(MessageRecord.channel_id == channel_id)
            .where(MessageRecord.created_at >= cutoff)
        ) or 0
        users = s.scalar(
            select(func.count(MessageRecord.user_id.distinct()))
            .where(MessageRecord.channel_id == channel_id)
            .where(MessageRecord.created_at >= cutoff)
        ) or 0
    return f"#{channel_id}  last {days}d:  {total} messages,  {users} active users"


def list_channels(db: Database) -> str:
    with Session(db._engine) as s:
        rows = list(s.execute(
            select(MessageRecord.channel_id, func.count().label("n"))
            .group_by(MessageRecord.channel_id)
            .order_by(func.count().desc())
        ))
    if not rows:
        return "No channels in DB"
    lines = ["Channels:"]
    for channel_id, n in rows:
        lines.append(f"  {channel_id:30s}  {n} messages")
    return "\n".join(lines)
