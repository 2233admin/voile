"""End-to-end smoke test: Health -> Consumer -> TopicWorker.

Usage:
    cd D:/projects/voile
    redis-cli lpush voile:raw_queue '{"post_type":"message","message_id":"s1","user_id":"42","group_id":"100","raw_message":"今天天气真好","time":1712908800}'
    redis-cli lpush voile:raw_queue '{"post_type":"message","message_id":"s2","user_id":"42","group_id":"100","raw_message":"量子力学有新进展","time":1712908860}'
    python smoke_test.py
"""
from __future__ import annotations

import sys
import time
import urllib.request
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.health import HealthServer
from core.ingest.consumer import RedisConsumer
from core.agents.topic_worker import TopicWorker
from core.storage.db import Database, MessageRecord, MessageTopic

REDIS_URL = "redis://localhost:6379/0"
DB_URL = "sqlite:///smoke.db"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def check(label: str, cond: bool, detail: str = "") -> bool:
    tag = PASS if cond else FAIL
    print(f"  [{tag}] {label}" + (f" — {detail}" if detail else ""))
    return cond


def step_health() -> bool:
    print("\n=== Step 1: HealthServer ===")
    s = HealthServer({})
    s.start()
    time.sleep(0.2)
    try:
        raw = urllib.request.urlopen("http://localhost:8765/health", timeout=2).read()
        ok = b'"status": "ok"' in raw
        check("GET /health returns 200 + status:ok", ok, raw.decode())
        return ok
    except Exception as exc:
        check("GET /health", False, str(exc))
        return False
    finally:
        s.stop()


def step_consumer(db: Database) -> int:
    print("\n=== Step 2: RedisConsumer ===")
    c = RedisConsumer(db, redis_url=REDIS_URL, cleaner_addr=None)
    try:
        n = c.run_once()
    except Exception as exc:
        check("run_once()", False, str(exc))
        return 0

    with Session(db._engine) as s:
        rows = list(s.scalars(select(MessageRecord)))

    check("redis reachable + messages consumed", n > 0, f"{n} messages")
    check("MessageRecord rows written", len(rows) > 0, f"{len(rows)} rows")
    for r in rows:
        print(f"    msg_id={r.message_id} channel={r.channel_id} content={r.content!r}")
    return n


def step_topic(db: Database) -> int:
    print("\n=== Step 3: TopicWorker ===")
    w = TopicWorker(db, ann_addr=None)
    try:
        n = w.process_untagged()
    except Exception as exc:
        check("process_untagged()", False, str(exc))
        return 0

    with Session(db._engine) as s:
        topics = list(s.scalars(select(MessageTopic).order_by(MessageTopic.id)))

    check("messages tagged", n > 0, f"{n} tagged")
    check("MessageTopic rows written", len(topics) > 0, f"{len(topics)} rows")
    for t in topics:
        print(f"    msg_id={t.message_id} label={t.topic_label} sim={t.similarity_score:.3f}")
    return n


def main() -> None:
    db = Database(DB_URL)

    ok1 = step_health()
    n2 = step_consumer(db)
    n3 = step_topic(db)

    print("\n=== Summary ===")
    all_pass = ok1 and n2 > 0 and n3 > 0
    if all_pass:
        print(f"  [{PASS}] all steps passed")
    else:
        print(f"  [{FAIL}] some steps failed — check output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
