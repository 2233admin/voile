#!/usr/bin/env python3
"""Voile runner -- starts all workers. Usage: python run.py [--help]"""
from __future__ import annotations

import argparse
import logging
import os
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("voile.runner")


def main() -> None:
    parser = argparse.ArgumentParser(description="Voile worker runner")
    parser.add_argument("--db", default=os.environ.get("VOILE_DB_URL", "sqlite:///voile.db"))
    parser.add_argument("--redis", default=os.environ.get("VOILE_REDIS_URL", "redis://localhost:6379/0"))
    parser.add_argument("--obsidian", default=os.environ.get("VOILE_OBSIDIAN_VAULT"))
    parser.add_argument("--cleaner", default=os.environ.get("VOILE_CLEANER_ADDR", "localhost:50051"),
                        help="Rust cleaner gRPC addr (empty string to disable)")
    parser.add_argument("--ann", default=os.environ.get("VOILE_ANN_ADDR", "localhost:50052"),
                        help="Rust ann gRPC addr (empty string to disable)")
    parser.add_argument("--channel", default=None, help="Limit topic worker to one channel_id")
    args = parser.parse_args()

    cleaner_addr: str | None = args.cleaner if args.cleaner else None
    ann_addr: str | None = args.ann if args.ann else None

    from core.storage.db import Database
    from core.agents.sentiment_worker import SentimentWorker
    from core.agents.topic_worker import TopicWorker
    from core.agents.link_archiver import LinkArchiver
    from core.ingest.consumer import RedisConsumer
    from core.health import HealthServer

    db = Database(args.db)
    log.info("DB: %s", args.db)
    log.info("Redis: %s", args.redis)
    log.info("Obsidian vault: %s", args.obsidian or "(disabled)")
    log.info("Cleaner: %s", cleaner_addr or "(disabled)")
    log.info("ANN: %s", ann_addr or "(disabled)")

    workers: list[tuple[str, object]] = [
        ("consumer", RedisConsumer(db, redis_url=args.redis, cleaner_addr=cleaner_addr)),
        ("sentiment", SentimentWorker(db, obsidian_vault=args.obsidian)),
        ("topic", TopicWorker(db, channel_id=args.channel, obsidian_vault=args.obsidian, ann_addr=ann_addr)),
        ("links", LinkArchiver(db, redis_url=args.redis, obsidian_vault=args.obsidian)),
    ]

    threads = []
    threads_dict: dict[str, threading.Thread] = {}
    for name, worker in workers:
        t = threading.Thread(target=worker.run_forever, name=name, daemon=True)  # type: ignore[union-attr]
        t.start()
        threads.append(t)
        threads_dict[name] = t
        log.info("started %s", name)

    health = HealthServer(threads_dict)
    health.start()
    log.info("started health on port %d", health.port)

    log.info("all workers running -- Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("shutting down")


if __name__ == "__main__":
    main()
