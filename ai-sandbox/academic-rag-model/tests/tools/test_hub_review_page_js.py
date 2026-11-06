"""Runs the review page's own script against a fake DOM and an in-memory db (node), so decide / change /
overwrite / error behavior is tested without a browser. Skipped when node is not installed."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tools.hub_review import render_page

HARNESS = Path(__file__).with_name("hub_review_page_harness.js")

PAYLOAD = {"generated": "t", "items": [
    {"item_id": "aaa", "type": "relink", "subject_ids": ["f1"], "subject_paths": ["notes/old.md"], "status": "pending",
     "candidates": [{"path": "notes/new.md", "basis": "similarity", "score": 0.9,
                     "evidence": {"shared": "same words here", "new_opening": "x"}}]},
    {"item_id": "bbb", "type": "relink", "subject_ids": ["f2"], "subject_paths": ["notes/twin.md"], "status": "pending",
     "candidates": [{"path": "sets/one.md", "basis": "byte_hash", "score": 1.0},
                    {"path": "sets/two.md", "basis": "byte_hash", "score": 1.0}]},
]}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_review_page_decide_change_and_error_flow(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(render_page(PAYLOAD), encoding="utf-8")
    done = subprocess.run(["node", str(HARNESS), str(page)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr or done.stdout
    assert "PASS" in done.stdout
