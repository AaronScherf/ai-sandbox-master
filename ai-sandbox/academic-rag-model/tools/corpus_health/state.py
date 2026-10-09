from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from tools.corpus_health.finding import Finding
from tools.git_workflow import GitError, git_common_dir

STATE_VERSION = 1


class StateError(RuntimeError):
    pass


def default_state_dir(corpus_root: str | Path) -> Path:
    root = Path(corpus_root).resolve()
    try:
        common = git_common_dir(root)
    except GitError as exc:
        raise StateError(f"cannot resolve repository common directory: {exc}") from exc
    root_key = hashlib.sha256(os.path.normcase(str(root)).encode("utf-8")).hexdigest()[:16]
    return common / "corpus-health" / root_key


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _exclusive_lock(path: Path, timeout_seconds: float = 5.0) -> Iterator[None]:
    """Cross-process advisory lock; the OS releases it if the process exits."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            # Reading the byte before locking is denied by Windows while
            # another process holds its byte-range lock. File metadata stays
            # readable, so use size only to initialize an empty lock file.
            if os.fstat(handle.fileno()).st_size == 0:
                handle.seek(0)
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + timeout_seconds
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise StateError(f"timed out waiting for state lock {path}") from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            deadline = time.monotonic() + timeout_seconds
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise StateError(f"timed out waiting for state lock {path}") from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class StateStore:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.state_path = self.directory / "state.json"
        self.runs_path = self.directory / "runs.jsonl"
        self.lock_path = self.directory / "state.lock"

    def _load_unlocked(self) -> dict:
        if not self.state_path.exists():
            return {"version": STATE_VERSION, "findings": {}}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"cannot read state ledger {self.state_path}: {exc}") from exc
        if not isinstance(data, dict) or data.get("version") != STATE_VERSION or not isinstance(data.get("findings"), dict):
            raise StateError(f"unsupported or malformed state ledger: {self.state_path}")
        return data

    def _write_unlocked(self, data: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix="state-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, self.state_path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise

    @staticmethod
    def finding_id(finding: Finding) -> str:
        identity = [finding.root, finding.scope, finding.kind, finding.fingerprint or "", os.path.normcase(finding.path)]
        return hashlib.sha256("\0".join(identity).encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _content_identity(finding_data: dict) -> tuple[str, str, str, str]:
        return (
            str(finding_data.get("root", "")), str(finding_data.get("scope", "")),
            str(finding_data.get("kind", "")), str(finding_data.get("fingerprint") or ""),
        )

    @staticmethod
    def action_signature(finding: Finding) -> str:
        value = "\0".join((finding.suggested_action or "", finding.expected_output or "",
                            finding.cost_category))
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def refresh(self, findings: list[Finding]) -> list[Finding]:
        now = _now()
        with _exclusive_lock(self.lock_path):
            data = self._load_unlocked()
            entries: dict[str, dict] = data["findings"]
            current_ids: set[str] = set()
            current_locations = {
                (finding.root, finding.scope, finding.kind, os.path.normcase(finding.path))
                for finding in findings
            }
            result: list[Finding] = []
            for finding in findings:
                finding_id = self.finding_id(finding)
                entry = entries.get(finding_id)
                if entry is None:
                    identity = self._content_identity(finding.to_dict())
                    previous_locations = [
                        (old_id, candidate)
                        for old_id, candidate in entries.items()
                        if self._content_identity(candidate.get("finding", {})) == identity
                        and candidate.get("finding", {}).get("path") != finding.path
                        and (
                            str(candidate.get("finding", {}).get("root", "")),
                            str(candidate.get("finding", {}).get("scope", "")),
                            str(candidate.get("finding", {}).get("kind", "")),
                            os.path.normcase(str(candidate.get("finding", {}).get("path", ""))),
                        ) not in current_locations
                    ]
                    if previous_locations:
                        # Identical bytes do not prove a rename: a duplicate may have
                        # been added after the old path disappeared. Keep the new
                        # location pending and require a human to distinguish them.
                        finding = replace(
                            finding,
                            evidence=(
                                f"{finding.evidence}; identical content was previously recorded "
                                "at an absent path; possible rename or duplicate, review this location"
                            ),
                        )
                current_ids.add(finding_id)
                serialized = finding.to_dict()
                serialized["finding_id"] = finding_id
                signature = self.action_signature(finding)
                if entry is None:
                    entry = {
                        "finding_id": finding_id,
                        "status": "pending_review",
                        "first_seen": now,
                        "created_at": now,
                        "decision": None,
                    }
                elif entry.get("action_signature") != signature and entry.get("status") in {
                    "accepted", "declined", "deferred", "blocked", "failed",
                }:
                    entry["status"] = "pending_review"
                    entry["decision"] = None
                    entry["invalidated_at"] = now
                entry.update({
                    "finding": serialized,
                    "action_signature": signature,
                    "last_seen": now,
                    "status": entry.get("status", "pending_review"),
                })
                if entry["status"] == "vanished":
                    previous = entry.pop("previous_status", None)
                    entry["status"] = previous if previous in {"declined", "deferred"} else "pending_review"
                elif entry["status"] == "failed":
                    # A failed execution requires a fresh human decision after scan.
                    entry["status"] = "pending_review"
                    entry["decision"] = None
                entries[finding_id] = entry
                result.append(replace(finding, finding_id=finding_id))

            for finding_id, entry in entries.items():
                if finding_id not in current_ids and entry.get("status") != "vanished":
                    entry["previous_status"] = entry.get("status")
                    entry["status"] = "vanished"
                    entry["vanished_at"] = now
            self._write_unlocked(data)
        return result

    def pending(self, *, include_deferred: bool = False) -> list[dict]:
        with _exclusive_lock(self.lock_path):
            data = self._load_unlocked()
        statuses = {"pending_review"}
        if include_deferred:
            statuses.add("deferred")
        return [entry for entry in data["findings"].values() if entry.get("status") in statuses]

    def get_entry(self, finding_id: str) -> dict | None:
        with _exclusive_lock(self.lock_path):
            data = self._load_unlocked()
        return data["findings"].get(finding_id)

    def accepted(self) -> list[dict]:
        with _exclusive_lock(self.lock_path):
            data = self._load_unlocked()
        return [entry for entry in data["findings"].values()
                if entry.get("status") in {"accepted", "blocked"}]

    def record_action(self, finding_id: str, fingerprint: str | None, status: str,
                      detail: dict) -> dict:
        if status not in {"applied", "failed", "blocked", "pending_review"}:
            raise StateError(f"invalid action status: {status}")
        with _exclusive_lock(self.lock_path):
            data = self._load_unlocked()
            entry = data["findings"].get(finding_id)
            if entry is None or entry.get("status") not in {"accepted", "blocked"}:
                raise StateError("finding is no longer accepted")
            if entry.get("finding", {}).get("fingerprint") != fingerprint:
                raise StateError("finding fingerprint changed before action")
            entry["status"] = status
            entry["last_action"] = {"at": _now(), "status": status, **detail}
            if status == "pending_review":
                entry["decision"] = None
            self._write_unlocked(data)
            return entry

    def decide(self, finding_id: str, decision: str, fingerprint: str | None) -> dict:
        if decision not in {"accepted", "declined", "deferred"}:
            raise StateError(f"invalid review decision: {decision}")
        now = _now()
        with _exclusive_lock(self.lock_path):
            data = self._load_unlocked()
            entry = data["findings"].get(finding_id)
            if entry is None:
                raise StateError("finding is no longer present in the ledger")
            current = entry.get("finding", {}).get("fingerprint")
            if current != fingerprint:
                raise StateError("finding fingerprint changed; rescan before recording a decision")
            if decision == "accepted" and (not fingerprint or fingerprint.startswith("stat:")):
                raise StateError("cannot accept without a content fingerprint; run a deeper audit first")
            if entry.get("status") in {"vanished", "applied"}:
                raise StateError(f"finding cannot be reviewed in state {entry.get('status')}")
            if entry.get("status") not in {"pending_review", "deferred"}:
                raise StateError("finding already has a decision; rescan the pending queue")
            entry["status"] = decision
            entry["decision"] = {"status": decision, "at": now}
            self._write_unlocked(data)
            return entry

    def decide_many(self, decisions: list[dict]) -> list[dict]:
        if not decisions:
            return []
        if any(item.get("decision") not in {"accepted", "declined", "deferred"} for item in decisions):
            raise StateError("batch contains an invalid review decision")
        now = _now()
        with _exclusive_lock(self.lock_path):
            data = self._load_unlocked()
            entries: list[dict] = []
            for item in decisions:
                entry = data["findings"].get(item.get("finding_id"))
                if entry is None:
                    raise StateError("batch contains a finding no longer present in the ledger")
                if entry.get("finding", {}).get("fingerprint") != item.get("fingerprint"):
                    raise StateError("batch contains a stale finding; rescan before recording decisions")
                if item.get("decision") == "accepted" and (
                    not item.get("fingerprint") or str(item["fingerprint"]).startswith("stat:")
                ):
                    raise StateError("cannot accept a finding without a content fingerprint")
                if entry.get("status") in {"vanished", "applied"}:
                    raise StateError(f"batch contains a finding in state {entry.get('status')}")
                if entry.get("status") not in {"pending_review", "deferred"}:
                    raise StateError("batch contains a finding already decided")
                entries.append(entry)
            for entry, item in zip(entries, decisions, strict=True):
                entry["status"] = item["decision"]
                entry["decision"] = {"status": item["decision"], "at": now}
            self._write_unlocked(data)
            return entries

    def record_run(self, report: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"recorded_at": _now(), **report}, ensure_ascii=False, sort_keys=True)
        with _exclusive_lock(self.lock_path):
            with self.runs_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(line + "\n")
                stream.flush()
                os.fsync(stream.fileno())
