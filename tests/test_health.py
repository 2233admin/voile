"""Tests for core.health.HealthServer."""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from collections.abc import Generator

import pytest

from core.health import HealthServer


def _free_port() -> int:
    """Pick an ephemeral port by binding then releasing."""
    import socket
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _make_alive_thread() -> threading.Thread:
    stop = threading.Event()
    t = threading.Thread(target=stop.wait, daemon=True)
    t.start()
    return t


def _make_dead_thread() -> threading.Thread:
    t = threading.Thread(target=lambda: None, daemon=True)
    t.start()
    t.join()
    return t


@pytest.fixture()
def health_server() -> Generator[HealthServer, None, None]:
    port = _free_port()
    alive = _make_alive_thread()
    dead = _make_dead_thread()
    threads = {
        "consumer": alive,
        "sentiment": alive,
        "topic": alive,
        "links": dead,
    }
    server = HealthServer(threads, port=port)
    server.start()
    # Give the daemon thread a moment to bind
    time.sleep(0.05)
    yield server
    server.stop()


def _get(port: int, path: str = "/health") -> tuple[int, dict]:
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=3) as resp:
        return resp.status, json.loads(resp.read())


class TestHealthEndpoint:
    def test_responds_200(self, health_server: HealthServer) -> None:
        status, _ = _get(health_server.port)
        assert status == 200

    def test_json_structure(self, health_server: HealthServer) -> None:
        _, body = _get(health_server.port)
        assert body["status"] == "ok"
        assert "workers" in body
        assert "uptime_s" in body

    def test_worker_keys_present(self, health_server: HealthServer) -> None:
        _, body = _get(health_server.port)
        workers = body["workers"]
        assert set(workers.keys()) == {"consumer", "sentiment", "topic", "links"}

    def test_alive_workers_true(self, health_server: HealthServer) -> None:
        _, body = _get(health_server.port)
        workers = body["workers"]
        assert workers["consumer"] is True
        assert workers["sentiment"] is True
        assert workers["topic"] is True

    def test_dead_worker_false(self, health_server: HealthServer) -> None:
        _, body = _get(health_server.port)
        assert body["workers"]["links"] is False

    def test_uptime_is_positive_float(self, health_server: HealthServer) -> None:
        _, body = _get(health_server.port)
        assert isinstance(body["uptime_s"], float)
        assert body["uptime_s"] >= 0.0

    def test_unknown_path_returns_404(self, health_server: HealthServer) -> None:
        import urllib.error
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _get(health_server.port, "/unknown")
        assert exc_info.value.code == 404

    def test_custom_port_respected(self) -> None:
        port = _free_port()
        server = HealthServer({}, port=port)
        server.start()
        time.sleep(0.05)
        try:
            status, body = _get(port)
            assert status == 200
            assert body["workers"] == {}
        finally:
            server.stop()
