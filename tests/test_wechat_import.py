"""Tests for core.importers.wechat_import (XAR-15)."""
from __future__ import annotations

import csv
import sqlite3
import tempfile
from pathlib import Path

from core.importers.wechat_import import import_csv, import_sqlite
from core.storage.db import Database

_ROWS = [
    {"MsgSvrId": "1001", "Type": "1", "IsSender": "0", "CreateTime": "1712908800",
     "StrContent": "hello", "StrTalker": "wxid_friend"},
    {"MsgSvrId": "1002", "Type": "1", "IsSender": "1", "CreateTime": "1712908900",
     "StrContent": "world", "StrTalker": "wxid_friend"},
    {"MsgSvrId": "1003", "Type": "3", "IsSender": "0", "CreateTime": "1712909000",
     "StrContent": "[image]", "StrTalker": "wxid_friend"},
]

_FIELDS = ["MsgSvrId", "Type", "IsSender", "CreateTime", "StrContent", "StrTalker"]


def _write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_sqlite(rows: list[dict], path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE MSG (MsgSvrId TEXT, Type INTEGER, IsSender INTEGER, "
        "CreateTime INTEGER, StrContent TEXT, StrTalker TEXT)"
    )
    conn.executemany(
        "INSERT INTO MSG VALUES "
        "(:MsgSvrId, :Type, :IsSender, :CreateTime, :StrContent, :StrTalker)",
        rows,
    )
    conn.commit()
    conn.close()


def test_import_csv_basic():
    db = Database("sqlite:///:memory:")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = Path(f.name)
    _write_csv(_ROWS, csv_path)

    inserted, skipped = import_csv(csv_path, db)

    assert inserted == 3
    assert skipped == 0
    rows = db.recent("wxid_friend", limit=10)
    assert len(rows) == 3
    ids = {r.message_id for r in rows}
    assert ids == {"1001", "1002", "1003"}
    # user_id mapping
    sender_row = next(r for r in rows if r.message_id == "1002")
    assert sender_row.user_id == "self"
    receiver_row = next(r for r in rows if r.message_id == "1001")
    assert receiver_row.user_id == "wxid_friend"


def test_import_sqlite_basic():
    db = Database("sqlite:///:memory:")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        sq_path = Path(f.name)
    _write_sqlite(_ROWS, sq_path)

    inserted, skipped = import_sqlite(sq_path, db)

    assert inserted == 3
    assert skipped == 0
    rows = db.recent("wxid_friend", limit=10)
    assert len(rows) == 3


def test_import_dedup():
    db = Database("sqlite:///:memory:")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = Path(f.name)
    _write_csv(_ROWS, csv_path)

    inserted1, skipped1 = import_csv(csv_path, db)
    inserted2, skipped2 = import_csv(csv_path, db)

    assert inserted1 == 3
    assert inserted2 == 0
    assert skipped2 == 3
    # total in DB unchanged
    assert len(db.recent("wxid_friend", limit=100)) == 3


def test_import_since_filter():
    db = Database("sqlite:///:memory:")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        csv_path = Path(f.name)
    _write_csv(_ROWS, csv_path)

    # since=1712908850 excludes the first row (ts=1712908800)
    inserted, skipped = import_csv(csv_path, db, since=1712908850)

    assert inserted == 2
    rows = db.recent("wxid_friend", limit=10)
    assert len(rows) == 2
    ids = {r.message_id for r in rows}
    assert "1001" not in ids
    assert "1002" in ids
    assert "1003" in ids
