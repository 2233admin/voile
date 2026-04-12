"""XAR-21: Decision Tracker Agent.

Detects decision-type conversations in group chat using keyword heuristics,
extracts decision process, and writes to Obsidian decision log.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.storage.db import Database, MessageRecord

PROPOSAL_KW = ["提议", "建议", "我觉得我们应该", "要不要", "能不能", "是否"]
DISCUSSION_KW = ["同意", "不同意", "反对", "支持", "但是", "然而", "不过"]
CONCLUSION_KW = ["决定", "确定", "就这样", "拍板", "定了", "好的就", "通过"]

WINDOW_SIZE = 20


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _extract_title(messages: list[MessageRecord]) -> str:
    """Use the first proposal message content as the decision title (truncated)."""
    for msg in messages:
        if _contains_any(msg.content, PROPOSAL_KW):
            title = msg.content[:50].strip()
            return title if title else "未命名决议"
    return "未命名决议"


def _extract_conclusion(messages: list[MessageRecord]) -> str:
    """Return the last conclusion-keyword message content."""
    for msg in reversed(messages):
        if _contains_any(msg.content, CONCLUSION_KW):
            return msg.content
    return ""


def detect_decision_segment(messages: list[MessageRecord]) -> list[dict[str, Any]]:
    """Sliding window of 20 messages; yield decision dicts where
    the window contains >=1 PROPOSAL_KW hit AND >=1 CONCLUSION_KW hit.

    Returns list of dicts:
        title, proposal, discussion_count, conclusion,
        participants, message_ids, start_at, end_at
    """
    results: list[dict[str, Any]] = []
    seen_end_ids: set[str] = set()  # deduplicate overlapping windows

    n = len(messages)
    for start in range(n):
        end = min(start + WINDOW_SIZE, n)
        window = messages[start:end]

        has_proposal = any(_contains_any(m.content, PROPOSAL_KW) for m in window)
        has_conclusion = any(_contains_any(m.content, CONCLUSION_KW) for m in window)

        if not (has_proposal and has_conclusion):
            continue

        # Deduplicate: skip if the last message of this window was already
        # the end of a previously emitted segment.
        end_msg_id = window[-1].message_id
        if end_msg_id in seen_end_ids:
            continue
        seen_end_ids.add(end_msg_id)

        proposal_msg = next(
            (m for m in window if _contains_any(m.content, PROPOSAL_KW)), window[0]
        )
        discussion_count = sum(
            1 for m in window if _contains_any(m.content, DISCUSSION_KW)
        )
        conclusion_text = _extract_conclusion(window)
        participants = list({m.user_id for m in window})
        message_ids = [m.message_id for m in window]

        results.append(
            {
                "title": _extract_title(window),
                "proposal": proposal_msg.content,
                "discussion_count": discussion_count,
                "conclusion": conclusion_text,
                "participants": participants,
                "message_ids": message_ids,
                "start_at": window[0].created_at,
                "end_at": window[-1].created_at,
            }
        )

    return results


class DecisionTracker:
    """Detects decisions in group chat and logs them to Obsidian."""

    def __init__(
        self,
        db: Database,
        channel_id: str | None = None,
        obsidian_vault: str | None = None,
    ) -> None:
        self.db = db
        self.channel_id = channel_id
        self.obsidian_vault = obsidian_vault

    def _fetch_recent_messages(self, days: int = 7) -> list[MessageRecord]:
        if self.channel_id is None:
            return []
        cutoff = datetime.now(UTC) - timedelta(days=days)
        with Session(self.db._engine) as s:
            return list(
                s.scalars(
                    select(MessageRecord)
                    .where(MessageRecord.channel_id == self.channel_id)
                    .where(MessageRecord.created_at >= cutoff)
                    .order_by(MessageRecord.created_at.asc())
                )
            )

    def run_once(self) -> list[dict[str, Any]]:
        """Fetch last 7 days of messages, detect decisions, write to Obsidian.

        Returns the list of decision dicts that were written.
        """
        messages = self._fetch_recent_messages(days=7)
        decisions = detect_decision_segment(messages)
        for decision in decisions:
            discussion_lines = [
                f"[{decision['start_at']}] participants: {', '.join(decision['participants'])}",
                f"proposal: {decision['proposal']}",
                f"discussion_count: {decision['discussion_count']}",
            ]
            if self.obsidian_vault is not None:
                from core.obsidian.writer import ObsidianWriter
                writer = ObsidianWriter(self.obsidian_vault)
                writer.write_decision(
                    title=decision["title"],
                    discussion=discussion_lines,
                    conclusion=decision["conclusion"],
                )
        return decisions

    def run_forever(self, sleep: float = 21600.0) -> None:
        """Loop forever, calling run_once() every sleep seconds."""
        while True:
            self.run_once()
            time.sleep(sleep)
