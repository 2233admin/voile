"""Lightweight HTTP health endpoint for Voile.

Usage:
    server = HealthServer({"consumer": t1, "sentiment": t2, "topic": t3, "links": t4})
    server.start()  # spawns daemon thread
"""
from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict

_start_time = time.monotonic()

PORT_DEFAULT = 8765


class _HealthHandler(BaseHTTPRequestHandler):
    """Handles GET /health; rejects everything else with 404."""

    # Injected by HealthServer before serving
    threads: Dict[str, threading.Thread] = {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        workers = {name: t.is_alive() for name, t in self.threads.items()}
        payload = {
            "status": "ok",
            "workers": workers,
            "uptime_s": round(time.monotonic() - _start_time, 3),
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Suppress default access log noise; voile uses its own logger
        pass


class HealthServer:
    """HTTP health server that reports worker liveness.

    Args:
        threads: mapping of worker name -> Thread object
        port: port to listen on (default: VOILE_HEALTH_PORT env var or 8765)
    """

    def __init__(
        self,
        threads: Dict[str, threading.Thread],
        port: int | None = None,
    ) -> None:
        self.port = port if port is not None else int(os.environ.get("VOILE_HEALTH_PORT", PORT_DEFAULT))

        # Build a handler class with threads bound via class attribute so
        # BaseHTTPRequestHandler (which instantiates per-request) can reach them
        # without needing a custom __init__.
        handler = type(
            "_BoundHealthHandler",
            (_HealthHandler,),
            {"threads": threads},
        )

        self._server = HTTPServer(("", self.port), handler)
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start serving in a daemon thread."""
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="health",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut down the HTTP server (used in tests)."""
        self._server.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=2)
