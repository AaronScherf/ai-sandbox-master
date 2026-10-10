"""Versioned, locked owner decisions; tracker text remains the source of truth."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from tools.corpus_health.state import _exclusive_lock
from tools.project_steering.parser import Task
from tools.project_steering.report import _write_atomic

VERSION = 1
EFFORT = {"unknown", "<2h", "half_day", "1_2_days", "larger"}
STATUSES = {"candidate", "in_progress", "deferred", "declined", "done"}


class DecisionError(ValueError):
    pass


class DecisionStore:
    def __init__(self, directory: Path):
        self.path = directory / "decisions.json"
        self.lock = directory / "decisions.lock"

    def _read(self) -> dict:
        if not self.path.exists():
            return {"version": VERSION, "revision": 0, "tasks": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or data.get("version") != VERSION
                or not isinstance(data.get("tasks"), dict)
                or not isinstance(data.get("revision"), int)):
            raise DecisionError("unsupported or malformed project-steering state")
        return data

    def read(self) -> dict:
        with _exclusive_lock(self.lock):
            return self._read()

    def _write(self, data: dict) -> None:
        _write_atomic(self.path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    def reconcile(self, tasks: tuple[Task, ...]) -> dict:
        with _exclusive_lock(self.lock):
            data = self._read()
            changed = False
            current = {task.task_id: task for task in tasks if not task.provisional}
            for task_id, task in current.items():
                entry = data["tasks"].get(task_id)
                if entry is None:
                    data["tasks"][task_id] = {
                        "fingerprint": task.fingerprint, "section": task.section,
                        "impact": None, "urgency": None, "effort": "unknown",
                        "depends_on": [], "rejected_suggestions": [], "status": "candidate", "defer_until": None,
                        "recheck": False, "vanished": False, "reviewed_at": None,
                    }
                    changed = True
                else:
                    if entry["fingerprint"] != task.fingerprint or entry["section"] != task.section:
                        entry.update(fingerprint=task.fingerprint, section=task.section, recheck=True)
                        if entry["status"] in {"deferred", "declined"}:
                            entry["status"] = "candidate"
                        changed = True
                    if entry.get("vanished"):
                        entry["vanished"] = False
                        changed = True
            for task_id, entry in data["tasks"].items():
                if task_id not in current and not entry.get("vanished"):
                    entry["vanished"] = True
                    changed = True
            if changed:
                data["revision"] += 1
                self._write(data)
            return data

    def decide(self, task: Task, *, revision: int, fingerprint: str, changes: dict) -> dict:
        if task.provisional:
            raise DecisionError("assign a stable ID before saving decisions")
        allowed = {"impact", "urgency", "effort", "depends_on", "rejected_suggestions", "status", "defer_until", "recheck"}
        if not changes or set(changes) - allowed:
            raise DecisionError("unsupported decision fields")
        for key in ("impact", "urgency"):
            if key in changes and (type(changes[key]) is not int or changes[key] not in range(4)):
                raise DecisionError(f"{key} must be an integer from 0 to 3")
        if "effort" in changes and changes["effort"] not in EFFORT:
            raise DecisionError("invalid effort band")
        if "status" in changes and changes["status"] not in STATUSES:
            raise DecisionError("invalid status")
        if "depends_on" in changes:
            deps = changes["depends_on"]
            if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps) or len(deps) != len(set(deps)) or task.task_id in deps:
                raise DecisionError("invalid dependency IDs")
        if "rejected_suggestions" in changes:
            rejected = changes["rejected_suggestions"]
            if not isinstance(rejected, list) or any(not isinstance(x, str) for x in rejected) or len(rejected) != len(set(rejected)):
                raise DecisionError("invalid rejected suggestions")
        if "defer_until" in changes and changes["defer_until"] is not None:
            date.fromisoformat(changes["defer_until"])
        if "recheck" in changes and changes["recheck"] is not False:
            raise DecisionError("recheck can only be acknowledged")
        with _exclusive_lock(self.lock):
            data = self._read()
            if data["revision"] != revision:
                raise DecisionError("stale state revision; reload review page")
            entry = data["tasks"].get(task.task_id)
            if not entry or entry.get("vanished") or entry["fingerprint"] != fingerprint or fingerprint != task.fingerprint:
                raise DecisionError("stale task fingerprint; rescan")
            if "depends_on" in changes and any(dep not in data["tasks"] or data["tasks"][dep].get("vanished") for dep in changes["depends_on"]):
                raise DecisionError("dependency target missing or vanished")
            if changes.get("status") == "deferred" and not (changes.get("defer_until") or entry.get("defer_until")):
                raise DecisionError("deferred status requires a date")
            entry.update(changes)
            entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            data["revision"] += 1
            self._write(data)
            return data
