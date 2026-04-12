"""Tests for XAR-14: QQ chat history importer."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.importers.qq_import import import_file
from core.storage import Database


SAMPLE_RECORDS = [
    {
        "MsgId": "1001",
        "GroupId": "9001",
        "SenderId": "8001",
        "Content": "hello world",
        "MsgType": 1,
        "Time": 1712908800,
    },
    {
        "MsgId": "1002",
        "GroupId": "9001",
        "SenderId": "8002",
        "Content": "second message",
        "MsgType": 1,
        "Time": 1712908900,
    },
    {
        "MsgId": "1003",
        "GroupId": "9001",
        "SenderId": "8003",
        "Content": "third message",
        "MsgType": 2,
        "Time": 1712909000,
    },
]


def make_json_file(records: list[dict], tmp_path: Path) -> Path:
    p = tmp_path / "export.json"
    p.write_text(json.dumps(records), encoding="utf-8")
    return p


def make_db(tmp_path: Path) -> Database:
    return Database(f"sqlite:///{tmp_path}/test.db")


def test_import_basic(tmp_path):
    db = make_db(tmp_path)
    path = make_json_file(SAMPLE_RECORDS, tmp_path)

    inserted, skipped = import_file(path, db)

    assert inserted == 3
    assert skipped == 0
    rows = db.recent("9001", limit=10)
    assert len(rows) == 3


def test_import_dedup(tmp_path):
    db = make_db(tmp_path)
    path = make_json_file(SAMPLE_RECORDS, tmp_path)

    inserted1, _ = import_file(path, db)
    inserted2, skipped2 = import_file(path, db)

    assert inserted1 == 3
    assert inserted2 == 0
    assert skipped2 == 3
    # total rows unchanged
    assert len(db.recent("9001", limit=10)) == 3


def test_import_since(tmp_path):
    db = make_db(tmp_path)
    path = make_json_file(SAMPLE_RECORDS, tmp_path)

    # since=1712908850 filters out record 1001 (Time=1712908800)
    inserted, skipped = import_file(path, db, since=1712908850)

    assert inserted == 2
    assert skipped == 1
    assert len(db.recent("9001", limit=10)) == 2


def test_import_limit(tmp_path):
    db = make_db(tmp_path)
    path = make_json_file(SAMPLE_RECORDS, tmp_path)

    inserted, skipped = import_file(path, db, limit=1)

    assert inserted == 1
    assert len(db.recent("9001", limit=10)) == 1
