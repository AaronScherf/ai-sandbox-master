"""Short-lived loopback review surface for owner decisions."""

from __future__ import annotations

import hashlib
import io
import json
import secrets
import threading
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from tools.project_steering.parser import parse_tracker
from tools.project_steering.ranking import rank
from tools.project_steering.state import DecisionError, DecisionStore
from tools.corpus_health.state import StateError

STATIC = Path(__file__).parent / "static"
MAX_BODY = 64 * 1024


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, tracker: Path, state_dir: Path, timeout: int = 900):
        self.tracker = tracker.resolve()
        self.store = DecisionStore(state_dir)
        self.token = secrets.token_urlsafe(32)
        self.timeout = timeout
        super().__init__(("127.0.0.1", 0), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    @property
    def url(self) -> str:
        return f"{self.origin}/?token={self.token}"

    def snapshot(self) -> tuple[str, tuple, dict]:
        source = self.tracker.read_bytes()
        parsed = parse_tracker(source.decode("utf-8-sig"))
        if self.tracker.read_bytes() != source:
            raise DecisionError("tracker changed during review; rescan")
        return hashlib.sha256(source).hexdigest(), parsed.tasks, self.store.read()


class Handler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, format: str, *args) -> None:
        return  # URLs contain a token.

    def send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        for key, value in {
            "Content-Type": content_type, "Content-Length": str(len(body)), "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'",
            "X-Frame-Options": "DENY",
        }.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, *, post: bool = False) -> bool:
        if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            return False
        if post:
            return (self.headers.get("Origin") == self.server.origin
                    and self.headers.get("X-Project-Steering-Token") == self.server.token)
        return parse_qs(urlsplit(self.path).query).get("token", [""])[0] == self.server.token

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if not self.authorized() or path not in {"/", "/review.js", "/api/tasks"}:
            self.send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        if path in {"/", "/review.js"}:
            name = "review.html" if path == "/" else "review.js"
            kind = "text/html; charset=utf-8" if path == "/" else "text/javascript; charset=utf-8"
            content = (STATIC / name).read_bytes()
            if path == "/":
                content = content.replace(b"token=placeholder", ("token=" + self.server.token).encode("ascii"))
            self.send(200, content, kind)
            return
        try:
            source_hash, tasks, state = self.server.snapshot()
            latest = json.loads((self.server.store.path.parent / "latest.json").read_text(encoding="utf-8"))
            if latest["source_sha256"] != source_hash:
                raise DecisionError("tracker changed since scan; run scan again")
            parsed = parse_tracker(self.server.tracker.read_text(encoding="utf-8-sig"))
            payload = {"source_sha256": source_hash, "revision": state["revision"],
                       "tracker_uri": self.server.tracker.as_uri(),
                       "ranking": rank(tasks, state), "tasks": [task.to_dict() for task in tasks],
                       "warnings": [item.to_dict() for item in parsed.warnings],
                       "notices": [item.to_dict() for item in parsed.notices]}
            self.send(200, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except (OSError, ValueError, KeyError, StateError) as exc:
            self.send(409, json.dumps({"error": str(exc)}).encode("utf-8"))

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if not self.authorized(post=True) or path not in {"/api/decision", "/api/close"}:
            self.send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError("invalid request size or content type")
            request = json.loads(self.rfile.read(length))
            if path == "/api/close":
                self.send(200, b"{}")
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            source_hash, tasks, _ = self.server.snapshot()
            if request.get("source_sha256") != source_hash:
                raise DecisionError("stale tracker snapshot")
            task = next((item for item in tasks if item.task_id == request.get("task_id")), None)
            if task is None:
                raise DecisionError("unknown task ID")
            data = self.server.store.decide(task, revision=request["revision"],
                                            fingerprint=request["fingerprint"], changes=request["changes"])
            self.send(200, json.dumps({"revision": data["revision"], "ranking": rank(tasks, data)}).encode("utf-8"))
        except (OSError, ValueError, KeyError, TypeError, StateError) as exc:
            self.send(409, json.dumps({"error": str(exc)}).encode("utf-8"))


def serve_review(tracker: Path, state_dir: Path) -> None:
    from tools.project_steering.cli import main

    with redirect_stdout(io.StringIO()):
        if main(["scan", "--tracker", str(tracker), "--state-dir", str(state_dir)]) != 0:
            raise DecisionError("scan is incomplete; resolve warnings before review")
    server = ReviewServer(tracker, state_dir)
    timer = threading.Timer(server.timeout, server.shutdown)
    timer.daemon = True
    timer.start()
    print(f"Project steering review: {server.url}")
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        server.server_close()
