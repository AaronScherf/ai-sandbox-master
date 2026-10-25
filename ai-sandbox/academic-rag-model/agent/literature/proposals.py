"""Terms the agent proposed because no vocabulary term fit. They wait here for a human decision; nothing is
added to a vocabulary automatically."""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from .transcript import normalize
from .vocab import DATA_DIR, validate_vocabulary


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

    def _get(self, items: list[dict], proposal_id: str) -> dict:
        for p in items:
            if p["id"] == proposal_id:
                if p["status"] != "open":
                    raise ValueError(f"proposal {proposal_id} is already {p['status']}")
                return p
        raise ValueError(f"no proposal {proposal_id}")

    def accept(self, proposal_id: str, term_id: str, label: str, *, parent: str | None = None,
               definition: str = "", vocab_dir=None) -> None:
        items = self.all()
        p = self._get(items, proposal_id)
        path = Path(vocab_dir or DATA_DIR) / f"{p['vocabulary']}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        term = {"id": term_id, "label": label, "source": "local"}
        if parent:
            term["parent"] = parent
        if definition:
            term["definition"] = definition
        data["terms"].append(term)
        data["version"] += 1
        problems = validate_vocabulary(data)
        if problems:
            raise ValueError("; ".join(problems))  # nothing has been written yet
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
        p["status"], p["term_id"] = "accepted", term_id
        self._save(items)

    def reject(self, proposal_id: str, reason: str = "") -> None:
        items = self.all()
        p = self._get(items, proposal_id)
        p["status"], p["reason"] = "rejected", reason
        self._save(items)

    def merge(self, proposal_id: str, term_id: str, reason: str = "") -> None:
        """The proposal means a term the vocabulary already has; records that proposed it can point at that term."""
        items = self.all()
        p = self._get(items, proposal_id)
        p["status"], p["term_id"] = "merged", term_id
        if reason:
            p["reason"] = reason
        self._save(items)

    def resolutions(self) -> dict[tuple, str]:
        """(file_id, vocabulary, normalized value) -> the term an accepted or merged proposal now stands for."""
        return {(p["file_id"], p["vocabulary"], normalize(p["value"])): p["term_id"]
                for p in self.all() if p["status"] in ("accepted", "merged") and p.get("term_id")}

    def rejected_keys(self) -> set[tuple]:
        """(file_id, vocabulary, normalized value) for every rejected proposal -- a human already decided the
        value is not a real taxonomy concept, so tiered_facts drops the matching fact instead of displaying its
        raw free text as if it were one."""
        return {(p["file_id"], p["vocabulary"], normalize(p["value"])) for p in self.all() if p["status"] == "rejected"}
