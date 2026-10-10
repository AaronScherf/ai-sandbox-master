"""Versioned, locked owner decisions; tracker text remains the source of truth."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from tools.corpus_health.state import _exclusive_lock
from tools.project_steering.parser import Task
from tools.project_steering.report import _write_atomic
from tools.project_steering.routing import FIELDS, VALUES

VERSION = 2
EFFORT = {"unknown", "<2h", "half_day", "1_2_days", "larger"}
STATUSES = {"candidate", "in_progress", "deferred", "declined", "done"}
SCORE_FIELDS = ("impact", "urgency", "effort")


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
        if (not isinstance(data, dict) or data.get("version") not in {1, VERSION}
                or not isinstance(data.get("tasks"), dict)
                or not isinstance(data.get("revision"), int)):
            raise DecisionError("unsupported or malformed project-steering state")
        # The v2 fields are optional; a v1 ledger is upgraded in memory and
        # persisted on its next owner decision or scan reconciliation.
        data["version"] = VERSION
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
            if any(field in changes for field in SCORE_FIELDS):
                entry["score_approved_fingerprint"] = task.fingerprint
            data["revision"] += 1
            self._write(data)
            return data

    def import_scores(self, tasks: tuple[Task, ...], payload: dict, *, revision: int,
                      source_sha256: str) -> dict:
        """Keep assistant estimates separate from owner-approved score fields."""
        if not isinstance(payload, dict) or set(payload) != {"source_sha256", "batch", "rows"}:
            raise DecisionError("invalid score draft envelope")
        if payload["source_sha256"] != source_sha256:
            raise DecisionError("stale score draft source hash")
        batch = payload["batch"]
        if not isinstance(batch, str) or not batch or len(batch) > 80 or not all(c.isalnum() or c in "_-" for c in batch):
            raise DecisionError("invalid score draft batch ID")
        rows = payload["rows"]
        if not isinstance(rows, list) or not rows:
            raise DecisionError("score draft has no rows")
        current = {task.task_id: task for task in tasks if not task.provisional}
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"id", "fingerprint", *SCORE_FIELDS, "confidence", "rationale"}:
                raise DecisionError("invalid score draft row")
            task_id = row["id"]
            if not isinstance(task_id, str) or task_id in seen or task_id not in current:
                raise DecisionError(f"duplicate or unknown score task ID: {task_id}")
            seen.add(task_id)
            if row["fingerprint"] != current[task_id].fingerprint:
                raise DecisionError(f"stale score draft fingerprint: {task_id}")
            if (type(row["impact"]) is not int or row["impact"] not in range(4)
                    or type(row["urgency"]) is not int or row["urgency"] not in range(4)
                    or not isinstance(row["effort"], str) or row["effort"] not in EFFORT
                    or not isinstance(row["confidence"], str) or row["confidence"] not in {"low", "medium", "high"}
                    or not isinstance(row["rationale"], str)):
                raise DecisionError(f"invalid score estimate: {task_id}")
        with _exclusive_lock(self.lock):
            data = self._read()
            if data["revision"] != revision:
                raise DecisionError("stale state revision; retry import")
            if any(task_id not in data["tasks"] or data["tasks"][task_id].get("fingerprint") != current[task_id].fingerprint
                   for task_id in seen):
                raise DecisionError("state is stale; rescan before score import")
            for row in rows:
                data["tasks"][row["id"]]["score_suggested"] = {
                    **{field: row[field] for field in SCORE_FIELDS},
                    "confidence": row["confidence"], "rationale": row["rationale"],
                    "fingerprint": row["fingerprint"], "batch": batch,
                }
            data["revision"] += 1
            self._write(data)
            return data

    def approve_scores(self, tasks: tuple[Task, ...], *, revision: int,
                       task_ids: list[str]) -> tuple[dict, dict]:
        if not isinstance(task_ids, list) or not task_ids or any(not isinstance(x, str) for x in task_ids) or len(task_ids) != len(set(task_ids)):
            raise DecisionError("select unique task IDs to approve")
        current = {task.task_id: task for task in tasks if not task.provisional}
        if any(task_id not in current for task_id in task_ids):
            raise DecisionError("unknown task ID in score approval")
        with _exclusive_lock(self.lock):
            data = self._read()
            if data["revision"] != revision:
                raise DecisionError("stale state revision; reload review page")
            applied: list[str] = []
            stale: list[str] = []
            for task_id in task_ids:
                entry = data["tasks"].get(task_id)
                suggestion = entry.get("score_suggested") if entry else None
                if (not entry or entry.get("vanished") or entry.get("recheck")
                        or not isinstance(suggestion, dict)
                        or suggestion.get("fingerprint") != current[task_id].fingerprint):
                    stale.append(task_id)
                    continue
                for field in SCORE_FIELDS:
                    if entry.get(field) is None or (field == "effort" and entry.get(field) == "unknown"):
                        entry[field] = suggestion[field]
                entry["score_approved_fingerprint"] = current[task_id].fingerprint
                entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                applied.append(task_id)
            if applied:
                data["revision"] += 1
                self._write(data)
            return data, {"applied": applied, "stale": stale}

    def import_routing(self, tasks: tuple[Task, ...], payload: dict, *, revision: int,
                       source_sha256: str) -> dict:
        """Import a whole proposed batch atomically; never approve a route."""
        if not isinstance(payload, dict) or set(payload) != {"source_sha256", "batch", "rows"}:
            raise DecisionError("invalid routing draft envelope")
        if payload["source_sha256"] != source_sha256:
            raise DecisionError("stale routing draft source hash")
        batch = payload["batch"]
        if not isinstance(batch, str) or not batch or len(batch) > 80 or not all(c.isalnum() or c in "_-" for c in batch):
            raise DecisionError("invalid routing draft batch ID")
        rows = payload["rows"]
        if not isinstance(rows, list) or not rows:
            raise DecisionError("routing draft has no rows")
        current = {task.task_id: task for task in tasks if not task.provisional}
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"id", "fingerprint", *FIELDS, "confidence", "rationale"}:
                raise DecisionError("invalid routing draft row")
            task_id = row["id"]
            if not isinstance(task_id, str) or task_id in seen or task_id not in current:
                raise DecisionError(f"duplicate or unknown task ID: {task_id}")
            seen.add(task_id)
            if row["fingerprint"] != current[task_id].fingerprint:
                raise DecisionError(f"stale routing draft fingerprint: {task_id}")
            if any(not isinstance(row[field], str) or row[field] not in VALUES[field] for field in FIELDS):
                raise DecisionError(f"invalid routing tag: {task_id}")
            if (not isinstance(row["confidence"], str) or row["confidence"] not in {"low", "medium", "high"}
                    or not isinstance(row["rationale"], str)):
                raise DecisionError(f"invalid routing explanation: {task_id}")
        if seen != set(current):
            raise DecisionError("routing draft must cover every current stable task")
        with _exclusive_lock(self.lock):
            data = self._read()
            if data["revision"] != revision:
                raise DecisionError("stale state revision; retry import")
            if any(task_id not in data["tasks"] or data["tasks"][task_id].get("fingerprint") != current[task_id].fingerprint
                   for task_id in seen):
                raise DecisionError("state is stale; rescan before routing import")
            for row in rows:
                entry = data["tasks"][row["id"]]
                for field in FIELDS:
                    entry[field + "_suggested"] = row[field]
                entry["suggested_batch"] = batch
                entry["suggested_fingerprint"] = row["fingerprint"]
            data["revision"] += 1
            self._write(data)
            return data

    def route_decide(self, task: Task, *, revision: int, fingerprint: str, changes: dict) -> dict:
        allowed = {*FIELDS, "not_before"}
        if task.provisional or not isinstance(changes, dict) or not changes or set(changes) - allowed:
            raise DecisionError("invalid route decision")
        for field in FIELDS:
            if (field in changes and changes[field] is not None and
                    (not isinstance(changes[field], str) or changes[field] not in VALUES[field])):
                raise DecisionError(f"invalid {field}")
        if "not_before" in changes and changes["not_before"] is not None:
            if not isinstance(changes["not_before"], str):
                raise DecisionError("invalid not_before")
            date.fromisoformat(changes["not_before"])
        with _exclusive_lock(self.lock):
            data = self._read()
            if data["revision"] != revision:
                raise DecisionError("stale state revision; reload review page")
            entry = data["tasks"].get(task.task_id)
            if not entry or entry.get("vanished") or entry["fingerprint"] != fingerprint or fingerprint != task.fingerprint:
                raise DecisionError("stale task fingerprint; rescan")
            for field in FIELDS:
                if field in changes:
                    entry[field] = changes[field]
                    entry[field + "_source"] = "owner" if changes[field] is not None else None
            if "not_before" in changes:
                entry["not_before"] = changes["not_before"]
            entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            data["revision"] += 1
            self._write(data)
            return data

    def batch_approve(self, tasks: tuple[Task, ...], *, revision: int,
                      task_ids: list[str]) -> tuple[dict, dict]:
        if not isinstance(task_ids, list) or not task_ids or any(not isinstance(x, str) for x in task_ids) or len(task_ids) != len(set(task_ids)):
            raise DecisionError("select unique task IDs to approve")
        current = {task.task_id: task for task in tasks if not task.provisional}
        if any(task_id not in current for task_id in task_ids):
            raise DecisionError("unknown task ID in batch approval")
        with _exclusive_lock(self.lock):
            data = self._read()
            if data["revision"] != revision:
                raise DecisionError("stale state revision; reload review page")
            applied: list[str] = []
            stale: list[str] = []
            for task_id in task_ids:
                entry = data["tasks"].get(task_id)
                if (not entry or entry.get("vanished") or
                        entry.get("suggested_fingerprint") != current[task_id].fingerprint or
                        any(entry.get(field + "_suggested") not in VALUES[field] for field in FIELDS)):
                    stale.append(task_id)
                    continue
                for field in FIELDS:
                    if entry.get(field + "_source") != "owner":
                        entry[field] = entry[field + "_suggested"]
                        entry[field + "_source"] = "owner"
                entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                applied.append(task_id)
            if applied:
                data["revision"] += 1
                self._write(data)
            return data, {"applied": applied, "stale": stale}
