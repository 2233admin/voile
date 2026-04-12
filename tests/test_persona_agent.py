"""Tests for XAR-20: PersonaAgent."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from core.agents.persona_agent import PersonaAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg(user_id: str, message_id: str, content: str, hour: int = 10) -> MagicMock:
    msg = MagicMock()
    msg.user_id = user_id
    msg.message_id = message_id
    msg.content = content
    msg.created_at = datetime(2024, 1, 15, hour, 0, 0, tzinfo=UTC)
    msg.channel_id = "ch1"
    return msg


def _agent(tmp_path) -> PersonaAgent:
    """Return a PersonaAgent backed by a real in-memory SQLite DB."""
    return PersonaAgent(
        db_url="sqlite:///:memory:",
        vault_path=str(tmp_path / "vault"),
        channel_id="ch1",
        window_days=30,
    )


# ---------------------------------------------------------------------------
# Test 1: build_profile returns correct structure with mocked DB
# ---------------------------------------------------------------------------

def test_build_profile_structure(tmp_path):
    agent = _agent(tmp_path)

    msgs = [
        _make_msg("u1", "m1", "hello world", hour=9),
        _make_msg("u1", "m2", "good morning", hour=10),
        _make_msg("u1", "m3", "great day", hour=9),
    ]

    topic_labels = ["tech", "tech", "news"]
    sentiment_labels = ["positive", "positive", "neutral"]

    with patch.object(agent.db, "_engine") as mock_engine:
        mock_session = MagicMock()
        mock_engine.__class__ = MagicMock  # satisfy context manager

        # scalars returns different things per call order
        mock_session.scalars.side_effect = [
            iter(msgs),           # MessageRecord query
            iter(topic_labels),   # MessageTopic query
            iter(sentiment_labels),  # MessageSentiment query
        ]
        mock_engine.connect = MagicMock()

        # Patch Session used inside build_profile
        with patch("core.agents.persona_agent.Session") as MockSession:
            MockSession.return_value.__enter__ = lambda s, *a: mock_session
            MockSession.return_value.__exit__ = MagicMock(return_value=False)

            profile = agent.build_profile("u1")

    assert "top_topics" in profile
    assert "sentiment_trend" in profile
    assert "message_count" in profile
    assert "active_hours" in profile
    assert "sample_quotes" in profile

    assert profile["message_count"] == 3
    assert profile["sentiment_trend"] == "positive"
    assert "tech" in profile["top_topics"]
    assert len(profile["top_topics"]) <= 5
    assert len(profile["sample_quotes"]) <= 3
    assert all(isinstance(h, int) for h in profile["active_hours"])


# ---------------------------------------------------------------------------
# Test 2: build_profile with no messages returns safe defaults
# ---------------------------------------------------------------------------

def test_build_profile_empty(tmp_path):
    agent = _agent(tmp_path)

    with patch("core.agents.persona_agent.Session") as MockSession:
        mock_session = MagicMock()
        mock_session.scalars.return_value = iter([])
        MockSession.return_value.__enter__ = lambda s, *a: mock_session
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        profile = agent.build_profile("u_nobody")

    assert profile["message_count"] == 0
    assert profile["top_topics"] == []
    assert profile["sentiment_trend"] == "neutral"
    assert profile["active_hours"] == []
    assert profile["sample_quotes"] == []


# ---------------------------------------------------------------------------
# Test 3: run_once fetches distinct users and calls write_persona for each
# ---------------------------------------------------------------------------

def test_run_once_calls_write_persona(tmp_path):
    agent = _agent(tmp_path)

    user_ids = ["alice", "bob", "carol"]

    fake_profile = {
        "top_topics": ["tech"],
        "sentiment_trend": "positive",
        "message_count": 5,
        "active_hours": [10, 14],
        "sample_quotes": ["hello"],
    }

    with patch("core.agents.persona_agent.Session") as MockSession:
        mock_session = MagicMock()
        mock_session.scalars.return_value = iter(user_ids)
        MockSession.return_value.__enter__ = lambda s, *a: mock_session
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(agent, "build_profile", return_value=fake_profile) as mock_build:
            with patch.object(agent.writer, "write_persona") as mock_write:
                result = agent.run_once("ch1")

    assert sorted(result) == sorted(user_ids)
    assert mock_build.call_count == 3
    assert mock_write.call_count == 3
    mock_write.assert_any_call("alice", fake_profile)
    mock_write.assert_any_call("bob", fake_profile)
    mock_write.assert_any_call("carol", fake_profile)


# ---------------------------------------------------------------------------
# Test 4: active_hours picks the top-3 most frequent hours
# ---------------------------------------------------------------------------

def test_build_profile_active_hours_ranking(tmp_path):
    agent = _agent(tmp_path)

    # hour 14 appears 4x, hour 9 appears 2x, hour 22 appears 1x
    msgs = (
        [_make_msg("u2", f"m{i}", f"msg{i}", hour=14) for i in range(4)]
        + [_make_msg("u2", f"m{i+10}", f"msg{i+10}", hour=9) for i in range(2)]
        + [_make_msg("u2", "m99", "late", hour=22)]
    )

    with patch("core.agents.persona_agent.Session") as MockSession:
        mock_session = MagicMock()
        mock_session.scalars.side_effect = [
            iter(msgs),   # messages
            iter([]),     # topics
            iter([]),     # sentiments
        ]
        MockSession.return_value.__enter__ = lambda s, *a: mock_session
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        profile = agent.build_profile("u2")

    assert profile["active_hours"][0] == 14   # most frequent first
    assert 9 in profile["active_hours"]
    assert len(profile["active_hours"]) <= 3


# ---------------------------------------------------------------------------
# Test 5: sample_quotes skips empty/whitespace-only content
# ---------------------------------------------------------------------------

def test_build_profile_sample_quotes_skip_empty(tmp_path):
    agent = _agent(tmp_path)

    msgs = [
        _make_msg("u3", "m1", "   "),      # whitespace only — skip
        _make_msg("u3", "m2", ""),         # empty — skip
        _make_msg("u3", "m3", "real msg"),
        _make_msg("u3", "m4", "another"),
    ]

    with patch("core.agents.persona_agent.Session") as MockSession:
        mock_session = MagicMock()
        mock_session.scalars.side_effect = [
            iter(msgs),
            iter([]),
            iter([]),
        ]
        MockSession.return_value.__enter__ = lambda s, *a: mock_session
        MockSession.return_value.__exit__ = MagicMock(return_value=False)

        profile = agent.build_profile("u3")

    assert "real msg" in profile["sample_quotes"]
    assert "another" in profile["sample_quotes"]
    assert "" not in profile["sample_quotes"]
    assert "   " not in profile["sample_quotes"]
