"""XAR-15: WeChat history importer (CSV + SQLite formats)."""
from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import timezone, datetime
from pathlib import Path

from core.schemas.message import Message, MessageType, Platform
from core.storage.db import Database

_TYPE_MAP: dict[int, MessageType] = {
    1: MessageType.TEXT,
    3: MessageType.IMAGE,
    43: MessageType.VIDEO,
    34: MessageType.VOICE,
    49: MessageType.FILE,
}


def _map_type(raw: int) -> MessageType:
    return _TYPE_MAP.get(raw, MessageType.UNKNOWN)


def _build_message(row: dict) -> Message:
    """Build a normalized Message from a raw WeChatMsg row dict."""
    is_sender = int(row["IsSender"]) == 1
    talker = str(row["StrTalker"])
    return Message(
        platform=Platform.WECHAT,
        channel_id=talker,
        user_id="self" if is_sender else talker,
        message_id=str(row["MsgSvrId"]),
        message_type=_map_type(int(row["Type"])),
        content=str(row["StrContent"]),
        raw_payload={k: row[k] for k in row},
        created_at=datetime.fromtimestamp(int(row["CreateTime"]), tz=timezone.utc),
    )


def import_csv(
    path: Path,
    db: Database,
    since: int | None = None,
    limit: int | None = None,
) -> tuple[int, int]:
    """Import from CSV export. Returns (inserted, skipped)."""
    inserted = skipped = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if since is not None and int(row["CreateTime"]) < since:
                continue
            msg = _build_message(row)
            if db.upsert(msg):
                inserted += 1
            else:
                skipped += 1
            if limit is not None and (inserted + skipped) >= limit:
                break
    return inserted, skipped


def import_sqlite(
    path: Path,
    db: Database,
    since: int | None = None,
    limit: int | None = None,
) -> tuple[int, int]:
    """Import from SQLite export. Returns (inserted, skipped)."""
    inserted = skipped = 0
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        query = "SELECT MsgSvrId, Type, IsSender, CreateTime, StrContent, StrTalker FROM MSG"
        params: list = []
        if since is not None:
            query += " WHERE CreateTime >= ?"
            params.append(since)
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        cursor = conn.execute(query, params)
        for sqlite_row in cursor:
            row = dict(sqlite_row)
            msg = _build_message(row)
            if db.upsert(msg):
                inserted += 1
            else:
                skipped += 1
    finally:
        conn.close()
    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import WeChat history into voile DB")
    parser.add_argument("file", type=Path)
    parser.add_argument("--db", default="sqlite:///voile.db")
    parser.add_argument("--since", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--format", choices=["csv", "sqlite"], default="csv")
    args = parser.parse_args()
    fn = import_sqlite if args.format == "sqlite" else import_csv
    inserted, skipped = fn(args.file, Database(args.db), args.since, args.limit)
    print(f"done: {inserted} inserted, {skipped} skipped")


if __name__ == "__main__":
    main()
