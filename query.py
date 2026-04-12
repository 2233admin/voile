#!/usr/bin/env python3
"""Voile query CLI -- inspect archived chat data without an LLM.

Usage examples:
  python query.py channels
  python query.py recent   --channel 123456
  python query.py topics   --channel 123456 --days 14
  python query.py sentiment --channel 123456
  python query.py links    --keyword python
  python query.py decisions --channel 123456
  python query.py stats    --channel 123456
"""
from __future__ import annotations

import argparse
import os
import sys


def _db(url: str):
    from core.storage.db import Database
    return Database(url)


def main() -> None:
    p = argparse.ArgumentParser(description="Query Voile DB")
    p.add_argument("--db", default=os.environ.get("VOILE_DB_URL", "sqlite:///voile.db"))
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("channels", help="List all channels")

    r = sub.add_parser("recent", help="Recent messages from a channel")
    r.add_argument("--channel", required=True)
    r.add_argument("--limit", type=int, default=50)

    t = sub.add_parser("topics", help="Topic summary for a channel")
    t.add_argument("--channel", required=True)
    t.add_argument("--days", type=int, default=7)

    s = sub.add_parser("sentiment", help="Sentiment breakdown for a channel")
    s.add_argument("--channel", required=True)
    s.add_argument("--days", type=int, default=7)

    lk = sub.add_parser("links", help="Archived links")
    lk.add_argument("--keyword", default=None)
    lk.add_argument("--limit", type=int, default=20)

    d = sub.add_parser("decisions", help="Detected decisions from a channel")
    d.add_argument("--channel", required=True)
    d.add_argument("--days", type=int, default=7)

    st = sub.add_parser("stats", help="Channel stats")
    st.add_argument("--channel", required=True)
    st.add_argument("--days", type=int, default=7)

    args = p.parse_args()

    sys.path.insert(0, os.path.dirname(__file__))
    from core.query import (
        archived_links,
        channel_stats,
        find_decisions,
        list_channels,
        recent_messages,
        sentiment_summary,
        topic_summary,
    )

    db = _db(args.db)

    if args.cmd == "channels":
        print(list_channels(db))
    elif args.cmd == "recent":
        print(recent_messages(db, args.channel, args.limit))
    elif args.cmd == "topics":
        print(topic_summary(db, args.channel, args.days))
    elif args.cmd == "sentiment":
        print(sentiment_summary(db, args.channel, args.days))
    elif args.cmd == "links":
        print(archived_links(db, args.keyword, args.limit))
    elif args.cmd == "decisions":
        print(find_decisions(db, args.channel, args.days))
    elif args.cmd == "stats":
        print(channel_stats(db, args.channel, args.days))


if __name__ == "__main__":
    main()
