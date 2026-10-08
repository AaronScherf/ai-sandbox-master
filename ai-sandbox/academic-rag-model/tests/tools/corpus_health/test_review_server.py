from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from tools.corpus_health.finding import Finding
from tools.corpus_health.review_server import ReviewServer
from tools.corpus_health.state import StateStore


def _running_server(tmp_path):
    store = StateStore(tmp_path / "state")
    store.refresh([Finding("index_card_missing", "notes", "notes/econ/a.md", "a.md",
                           "missing card", suggested_action="index", fingerprint="sha256:x")])
    server = ReviewServer(store, timeout_seconds=30)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    return store, server, thread


def test_review_server_serves_local_page_and_records_decision(tmp_path):
    store, server, thread = _running_server(tmp_path)
    try:
        assert server.server_address[0] == "127.0.0.1"
        page = urllib.request.urlopen(server.review_url, timeout=2).read().decode("utf-8")
        assert "Review choices are recorded locally" in page
        assert "token=placeholder" not in page
        script_url = f"{server.expected_origin}/review.js?token={server.token}"
        script = urllib.request.urlopen(script_url, timeout=2).read().decode("utf-8")
        assert "textContent" in script
        assert "innerHTML" not in script
        api_url = f"{server.expected_origin}/api/findings?token={server.token}"
        entries = json.loads(urllib.request.urlopen(api_url, timeout=2).read())
        assert len(entries) == 1
        entry = entries[0]
        request = urllib.request.Request(
            f"{server.expected_origin}/api/decision",
            data=json.dumps({"finding_id": entry["finding_id"], "fingerprint": "sha256:x",
                             "decision": "accepted"}).encode(),
            headers={"Content-Type": "application/json", "X-Corpus-Health-Token": server.token,
                     "Origin": server.expected_origin},
            method="POST",
        )
        response = json.loads(urllib.request.urlopen(request, timeout=2).read())
        assert response["status"] == "accepted"
        assert store.pending() == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_review_server_rejects_bad_origin_and_stale_fingerprint(tmp_path):
    store, server, thread = _running_server(tmp_path)
    try:
        entry = store.pending()[0]
        headers = {"Content-Type": "application/json", "X-Corpus-Health-Token": server.token,
                   "Origin": "http://evil.invalid"}
        body = json.dumps({"finding_id": entry["finding_id"], "fingerprint": "sha256:x",
                           "decision": "accepted"}).encode()
        bad_origin = urllib.request.Request(f"{server.expected_origin}/api/decision", data=body,
                                            headers=headers, method="POST")
        try:
            urllib.request.urlopen(bad_origin, timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("bad Origin was accepted")

        headers["Origin"] = server.expected_origin
        stale = json.dumps({"finding_id": entry["finding_id"], "fingerprint": "changed",
                            "decision": "accepted"}).encode()
        bad_fingerprint = urllib.request.Request(f"{server.expected_origin}/api/decision", data=stale,
                                                 headers=headers, method="POST")
        try:
            urllib.request.urlopen(bad_fingerprint, timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        else:
            raise AssertionError("stale fingerprint was accepted")
        assert store.pending()[0]["status"] == "pending_review"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_review_server_rejects_current_finding_that_has_been_resolved(tmp_path):
    store, server, thread = _running_server(tmp_path)
    server.validator = lambda _entries: False
    try:
        entry = store.pending()[0]
        request = urllib.request.Request(
            f"{server.expected_origin}/api/decision",
            data=json.dumps({"finding_id": entry["finding_id"], "fingerprint": "sha256:x",
                             "decision": "accepted"}).encode(),
            headers={"Content-Type": "application/json", "X-Corpus-Health-Token": server.token,
                     "Origin": server.expected_origin},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        else:
            raise AssertionError("resolved finding was accepted")
        assert store.pending()[0]["status"] == "pending_review"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
