"""Tests for ObsidianWriter -- XAR-22."""

from pathlib import Path

from core.obsidian import ObsidianWriter


def test_write_link(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    result = writer.write_link(
        url="https://example.com",
        title="Example Site",
        summary="A test summary.",
        tags=["test", "example"],
    )
    assert result is not None
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "url: https://example.com" in content
    assert "title: Example Site" in content
    assert "archived_at:" in content
    assert "- test" in content
    assert "- example" in content
    assert "A test summary." in content
    assert "[Source](https://example.com)" in content


def test_write_topic_card(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    result = writer.write_topic_card(
        topic="Python Tips",
        messages=["Use list comprehensions", "Prefer pathlib over os.path"],
        date="2026-04-12",
    )
    assert result is not None
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "date: 2026-04-12" in content
    assert "topic: Python Tips" in content
    assert "message_count: 2" in content
    assert "> Use list comprehensions" in content
    assert "> Prefer pathlib over os.path" in content


def test_write_persona(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    result = writer.write_persona(
        user_id="boris",
        profile={"language": "Chinese", "timezone": "Australia/Sydney"},
    )
    assert result is not None
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "user_id: boris" in content
    assert "updated_at:" in content
    assert "## language" in content
    assert "Chinese" in content
    assert "## timezone" in content
    assert "Australia/Sydney" in content


def test_write_decision(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path)
    result = writer.write_decision(
        title="Use SQLite for local storage",
        discussion=["Postgres is overkill", "SQLite has zero deps"],
        conclusion="SQLite chosen for simplicity.",
    )
    assert result is not None
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "title: Use SQLite for local storage" in content
    assert "## Discussion" in content
    assert "- Postgres is overkill" in content
    assert "- SQLite has zero deps" in content
    assert "## Conclusion" in content
    assert "SQLite chosen for simplicity." in content


def test_nonexistent_vault(tmp_path: Path) -> None:
    writer = ObsidianWriter(tmp_path / "does_not_exist")
    assert writer.write_link("https://x.com", "X", "summary", ["tag"]) is None
    assert writer.write_topic_card("topic", ["msg"], "2026-01-01") is None
    assert writer.write_persona("user", {"k": "v"}) is None
    assert writer.write_decision("title", ["point"], "conclusion") is None
