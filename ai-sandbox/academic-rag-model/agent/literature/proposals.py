"""Terms the agent proposed because no vocabulary term fit. They wait here for a human decision; nothing is
added to a vocabulary automatically."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .transcript import normalize


class Proposals:
    def __init__(self, directory):
        self.path = Path(directory) / "_proposals.json"

    def all(self) -> list[dict]:
        if not self.path.is_file():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def open(self) -> list[dict]:
        return [p for p in self.all() if p["status"] == "open"]

    def _save(self, items: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, self.path)

    def add(self, file_id: str, vocabulary: str, value: str, quote: str, locator, pass_label: str = "a") -> bool:
        """False when this paper already proposed this value for this vocabulary (any pass, any status)."""
        items = self.all()
        key = (file_id, vocabulary, normalize(value))
        if any((p["file_id"], p["vocabulary"], normalize(p["value"])) == key for p in items):
            return False
        items.append({"id": f"P{len(items) + 1:04d}", "file_id": file_id, "vocabulary": vocabulary, "value": value,
                      "quote": quote, "locator": locator, "pass": pass_label, "status": "open"})
        self._save(items)
        return True
