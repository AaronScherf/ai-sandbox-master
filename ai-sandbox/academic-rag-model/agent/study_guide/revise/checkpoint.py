# agent/study_guide/revise/checkpoint.py
"""Save each finished unit of a revise run (a stage, or one audited section) so a crashed run can resume.

The file is keyed on the inputs (guide hash, spec hash); a different key means the old work is ignored."""
from __future__ import annotations

import json
import os
from pathlib import Path


class Checkpoint:
    def __init__(self, path: str | Path, key: str):
        self.path, self.key = Path(path), key
        self.used: list[str] = []
        self._done: dict[str, object] = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("key") == key:
                self._done = dict(data.get("done", {}))
        except (OSError, ValueError, AttributeError):
            pass

    def get(self, name: str):
        if name in self._done:
            self.used.append(name)
            return self._done[name]
        return None

    def put(self, name: str, payload) -> None:
        self._done[name] = payload
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"key": self.key, "done": self._done}, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, self.path)

    def clear(self) -> None:
        self._done = {}
        for p in (self.path, self.path.with_suffix(".tmp")):
            try:
                p.unlink()
            except OSError:
                pass
