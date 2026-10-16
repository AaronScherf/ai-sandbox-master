"""study_record.json files, one per paper, keyed by the index card's file_id. The records are the source of truth;
any database built on top is derived and rebuildable (spec architecture A)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def check_file_id(file_id: str) -> str:
    """A file_id becomes a file name, so it may not carry a path or odd characters."""
    if not isinstance(file_id, str) or not _SAFE.match(file_id):
        raise ValueError(f"invalid file_id {file_id!r}: letters, digits, hyphens and underscores only")
    return file_id


class RecordStore:
    def __init__(self, root: str | Path):
        self.dir = Path(root)

    def path(self, file_id: str, pass_label: str = "a") -> Path:
        check_file_id(file_id)
        name = f"{file_id}.json" if pass_label == "a" else f"{file_id}.{pass_label}.json"
        return self.dir / name

    def read(self, file_id: str, pass_label: str = "a") -> dict | None:
        p = self.path(file_id, pass_label)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def write(self, record: dict, pass_label: str = "a") -> Path:
        p = self.path(record["identity"]["file_id"], pass_label)
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, p)
        return p

    def ids(self) -> list[str]:
        if not self.dir.is_dir():
            return []
        return sorted(p.stem for p in self.dir.glob("*.json") if p.stem.count(".") == 0 and not p.name.startswith("_"))
