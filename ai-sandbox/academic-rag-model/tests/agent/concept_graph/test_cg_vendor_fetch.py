import hashlib
import json

import pytest

from agent.concept_graph.vendor_fetch import fetch_all


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


def make_lock(tmp_path, sha=None):
    lock = tmp_path / "vendor.lock.json"
    lock.write_text(json.dumps({"files": [{"file": "lib.js", "url": "https://example.test/lib.js", "sha256": sha}]}), encoding="utf-8")
    return lock


def test_first_fetch_records_the_hash(tmp_path):
    lock = make_lock(tmp_path)
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    fetch_all(vendor, lock, opener=lambda url: FakeResponse(b"console.log(1)"))
    assert (vendor / "lib.js").read_bytes() == b"console.log(1)"
    assert json.loads(lock.read_text(encoding="utf-8"))["files"][0]["sha256"] == hashlib.sha256(b"console.log(1)").hexdigest()


def test_a_changed_download_is_rejected(tmp_path):
    lock = make_lock(tmp_path, sha=hashlib.sha256(b"original").hexdigest())
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    with pytest.raises(ValueError, match="lib.js"):
        fetch_all(vendor, lock, opener=lambda url: FakeResponse(b"tampered"))
    assert not (vendor / "lib.js").exists()
