"""Obsidian vault writer -- XAR-22."""

import re
from datetime import datetime, timezone
from pathlib import Path


def _slug(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


class ObsidianWriter:
    """Write/update markdown files in an Obsidian vault.
    All methods are no-ops if vault_path doesn't exist (graceful degradation).
    """

    def __init__(self, vault_path: str | Path):
        self.vault = Path(vault_path)

    def write_link(self, url: str, title: str, summary: str, tags: list[str]) -> Path | None:
        """Write a link archive note to links/{slugified_title}.md"""
        if not self.vault.exists():
            return None
        now = datetime.now(timezone.utc).isoformat()
        tags_yaml = "\n".join(f"  - {t}" for t in tags)
        slug = _slug(title)[:80]
        content = f"---\nurl: {url}\ntitle: {title}\ntags:\n{tags_yaml}\narchived_at: {now}\n---\n\n# {title}\n\n{summary}\n\n[Source]({url})\n"
        dest = self.vault / "links"
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / f"{slug}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def write_topic_card(self, topic: str, messages: list[str], date: str) -> Path | None:
        """Write a topic card to topics/{date}-{slug}.md"""
        if not self.vault.exists():
            return None
        slug = _slug(topic)
        filename = f"{date}-{slug}"[:80]
        blockquotes = "\n\n".join(f"> {m}" for m in messages)
        content = f"---\ndate: {date}\ntopic: {topic}\nmessage_count: {len(messages)}\n---\n\n# {topic}\n\n{blockquotes}\n"
        dest = self.vault / "topics"
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / f"{filename}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def write_persona(self, user_id: str, profile: dict) -> Path | None:
        """Write/update a persona profile to personas/{user_id}.md"""
        if not self.vault.exists():
            return None
        now = datetime.now(timezone.utc).isoformat()
        sections = "\n\n".join(f"## {k}\n\n{v}" for k, v in profile.items())
        content = f"---\nuser_id: {user_id}\nupdated_at: {now}\n---\n\n# {user_id}\n\n{sections}\n"
        dest = self.vault / "personas"
        dest.mkdir(parents=True, exist_ok=True)
        slug = _slug(user_id)[:80]
        path = dest / f"{slug}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def write_decision(self, title: str, discussion: list[str], conclusion: str) -> Path | None:
        """Write a decision log to decisions/{date}-{slug}.md"""
        if not self.vault.exists():
            return None
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = _slug(title)
        filename = f"{date}-{slug}"[:80]
        items = "\n".join(f"- {d}" for d in discussion)
        content = f"---\ndate: {date}\ntitle: {title}\n---\n\n# {title}\n\n## Discussion\n\n{items}\n\n## Conclusion\n\n{conclusion}\n"
        dest = self.vault / "decisions"
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / f"{filename}.md"
        path.write_text(content, encoding="utf-8")
        return path
