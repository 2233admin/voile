"""XAR-14: QQ chat history importer (qq-chat-exporter JSON format)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timezone, datetime
from pathlib import Path

from core.schemas import Message, Platform, MessageType
from core.storage import Database

MSG_TYPE_MAP: dict[int, str] = {
    1: "text",
    2: "image",
    43: "video",
    34: "voice",
    49: "file",
}


def import_file(
    path: Path,
    db: Database,
    since: int | None = None,
    limit: int | None = None,
) -> tuple[int, int]:
    """Import QQ JSON export file into db.

    Returns (inserted, skipped).
    """
    with path.open(encoding="utf-8") as f:
        records = json.load(f)

    inserted = 0
    skipped = 0
    processed = 0

    for raw in records:
        if limit is not None and processed >= limit:
            break

        try:
            ts: int = raw["Time"]
            if since is not None and ts < since:
                skipped += 1
                continue

            msg_type_str = MSG_TYPE_MAP.get(raw.get("MsgType", 0), "unknown")

            msg = Message(
                platform=Platform.QQ,
                channel_id=str(raw["GroupId"]),
                user_id=str(raw["SenderId"]),
                message_id=str(raw["MsgId"]),
                message_type=MessageType(msg_type_str),
                content=raw.get("Content", ""),
                raw_payload=raw,
                created_at=datetime.fromtimestamp(ts, tz=timezone.utc),
            )

            if db.upsert(msg):
                inserted += 1
            else:
                skipped += 1

            processed += 1

        except Exception as exc:
            print(f"warning: skipping record {raw.get('MsgId', '?')}: {exc}", file=sys.stderr)

    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import QQ chat history")
    parser.add_argument("file", type=Path)
    parser.add_argument("--db", default="sqlite:///voile.db")
    parser.add_argument("--since", type=int, help="Unix timestamp lower bound")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    inserted, skipped = import_file(args.file, Database(args.db), args.since, args.limit)
    print(f"done: {inserted} inserted, {skipped} skipped")


if __name__ == "__main__":
    main()
