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


def _post(server, path, payload):
    request = urllib.request.Request(
        f"{server.expected_origin}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Corpus-Health-Token": server.token,
                 "Origin": server.expected_origin},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(request, timeout=2).read())


def _add_relink(store):
    # Raised by core.indexer.reconcile_apply.raise_relink_items, never by a scan.
    return store.refresh([Finding("relink", "academic-hub-index", "academic_notes/econ/b.md", "Relink b.md",
                                  "ambiguous", suggested_action="choose", fingerprint="r1",
                                  scope="file_id:f1")], sweep_kinds=("relink",))[0]


def test_review_listing_excludes_self_refreshed_relink_entries(tmp_path):
    store, server, thread = _running_server(tmp_path)
    _add_relink(store)
    try:
        api_url = f"{server.expected_origin}/api/findings?token={server.token}"
        entries = json.loads(urllib.request.urlopen(api_url, timeout=2).read())
        assert [e["finding"]["kind"] for e in entries] == ["index_card_missing"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_bulk_decision_on_scan_findings_unaffected_by_relink_entry(tmp_path):
    store, server, thread = _running_server(tmp_path)
    relink = _add_relink(store)
    scan_ids = {e["finding_id"] for e in store.pending() if e["finding"]["kind"] != "relink"}
    server.validator = lambda entries: all(e["finding_id"] in scan_ids for e in entries)  # like a fresh scan
    try:
        entry = next(e for e in store.pending() if e["finding_id"] in scan_ids)
        result = _post(server, "/api/batch", {"decisions": [
            {"finding_id": entry["finding_id"], "fingerprint": "sha256:x", "decision": "declined"}]})
        assert result == {"updated": 1}
        assert store.get_entry(entry["finding_id"])["status"] == "declined"
        assert store.get_entry(relink.finding_id)["status"] == "pending_review"
        server.validator = None  # even without a scan validator, relink entries are not decidable here
        try:
            _post(server, "/api/decision", {"finding_id": relink.finding_id, "fingerprint": "r1",
                                            "decision": "accepted"})
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        else:
            raise AssertionError("relink entry was decided through the corpus-health review server")
        assert store.get_entry(relink.finding_id)["status"] == "pending_review"
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
