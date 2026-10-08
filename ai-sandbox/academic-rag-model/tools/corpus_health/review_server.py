from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlsplit

from tools.corpus_health.state import StateError, StateStore

_MAX_BODY_BYTES = 64 * 1024


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, store: StateStore, timeout_seconds: int = 900,
                 validator: Callable[[list[dict]], bool] | None = None,
                 include_deferred: bool = False):
        self.store = store
        self.validator = validator
        self.include_deferred = include_deferred
        self.token = secrets.token_urlsafe(32)
        self.review_timeout = timeout_seconds
        self.review_closed = threading.Event()
        super().__init__(("127.0.0.1", 0), _make_handler())
        self.expected_origin = f"http://127.0.0.1:{self.server_port}"

    @property
    def review_url(self) -> str:
        return f"{self.expected_origin}/?token={self.token}"


def _make_handler():
    class Handler(BaseHTTPRequestHandler):
        server: ReviewServer

        def log_message(self, fmt: str, *args) -> None:
            # Avoid writing token-bearing request URLs into console logs.
            return

        def _authorized_get(self, parsed) -> bool:
            token = parse_qs(parsed.query).get("token", [""])[0]
            return token == self.server.token and self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def _authorized_post(self) -> bool:
            return (
                self.headers.get("X-Corpus-Health-Token") == self.server.token
                and self.headers.get("Origin") == self.server.expected_origin
                and self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
            )

        def _send(self, status: int, payload: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            if parsed.path not in {"/", "/review.js", "/api/findings"} or not self._authorized_get(parsed):
                self._send(403, b"forbidden", "text/plain; charset=utf-8")
                return
            if parsed.path in {"/", "/review.js"}:
                filename = "review.html" if parsed.path == "/" else "review.js"
                html_path = Path(__file__).parent / "static" / filename
                try:
                    body = html_path.read_bytes()
                except OSError:
                    self._send(500, b"review page unavailable", "text/plain; charset=utf-8")
                    return
                if filename.endswith(".html"):
                    body = body.replace(b"token=placeholder", f"token={self.server.token}".encode("ascii"))
                content_type = "text/html; charset=utf-8" if filename.endswith(".html") else "text/javascript; charset=utf-8"
                self._send(200, body, content_type)
                return
            data = self.server.store.pending(include_deferred=self.server.include_deferred)
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")

        def do_POST(self) -> None:
            parsed = urlsplit(self.path)
            if parsed.path not in {"/api/decision", "/api/batch", "/api/close"} or not self._authorized_post():
                self._send(403, b"forbidden", "text/plain; charset=utf-8")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send(400, b"invalid content length", "text/plain; charset=utf-8")
                return
            if length <= 0 or length > _MAX_BODY_BYTES:
                self._send(413, b"invalid request size", "text/plain; charset=utf-8")
                return
            try:
                data = json.loads(self.rfile.read(length))
                if parsed.path == "/api/close":
                    self._send(200, b'{"closed":true}', "application/json; charset=utf-8")
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                if parsed.path == "/api/decision":
                    finding_id = str(data["finding_id"])
                    self._validate_current_many([finding_id])
                    result = self.server.store.decide(
                        finding_id, str(data["decision"]), data.get("fingerprint"),
                    )
                    payload = {"finding_id": result["finding_id"], "status": result["status"]}
                else:
                    self._validate_current_many([str(item["finding_id"]) for item in data["decisions"]])
                    result = self.server.store.decide_many(data["decisions"])
                    payload = {"updated": len(result)}
            except (json.JSONDecodeError, KeyError, TypeError, StateError) as exc:
                self._send(409 if isinstance(exc, StateError) else 400,
                           json.dumps({"error": str(exc)}).encode("utf-8"),
                           "application/json; charset=utf-8")
                return
            self._send(200, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

        def _validate_current_many(self, finding_ids: list[str]) -> None:
            if self.server.validator is None:
                return
            entries = [self.server.store.get_entry(finding_id) for finding_id in finding_ids]
            if any(entry is None for entry in entries) or not self.server.validator(entries):
                raise StateError("finding changed or no longer needs repair; run scan before reviewing")

    return Handler
