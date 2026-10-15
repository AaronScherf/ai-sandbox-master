"""
atomic_io.py
Shared atomic-write helper: writes JSON to a temp file in the same
directory as the target, then os.replace()s over it, so a crash
mid-write never leaves a half-written manifest or sidecar.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def write_json_atomic(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def write_bytes_atomic(path, data: bytes) -> None:
    """Same crash-safety as write_json_atomic, for PDF writes -- a crash
    mid-write (or another process reading the same path) never sees a
    half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise
