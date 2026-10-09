"""Explicitly approved, narrowly scoped corpus-health repairs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from core.indexer.audit import MarkdownIndexTarget, audit_markdown_index
from core.indexer.index_card import load_shard
from tools.corpus_health.config import ScanConfig
from tools.corpus_health.discovery import scan
from tools.corpus_health.state import StateError, StateStore

_CHUNK_KIND = "index_chunks_missing_or_stale"
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _redact(value: str) -> str:
    for name in ("GEMINI_API_KEY", "PAID_GEMINI_KEY", "GOOGLE_API_KEY"):
        secret = os.environ.get(name)
        if secret:
            value = value.replace(secret, "[redacted]")
    value = re.sub(r"(?i)\b(api[_-]?key|token|secret)\s*[:=]\s*\S+", r"\1=[redacted]", value)
    return value[:2000]


def _blocked_reason(kind: str) -> str:
    if kind in {"index_card_missing", "index_card_stale"}:
        return "no exact-file index-card reconciliation exists; rebuild scans a whole course"
    if kind in {"note_transcription_missing", "excalidraw_export_missing", "textbook_rag_output_missing"}:
        return "notes source pipeline quality and academic_notes sync-quiescence gates remain unresolved"
    if kind == "textbook_conversion_missing":
        return "remote textbook conversion is outside automated apply in v1"
    return "no reviewed exact-file repair adapter exists for this finding kind"


def _target(config: ScanConfig, index_path: str) -> tuple[str, Path]:
    path = PurePosixPath(index_path.replace("\\", "/"))
    parts = path.parts
    if path.is_absolute() or len(parts) < 3 or parts[0] not in {"academic_notes", "academic_resources"} or any(
        part in {".", ".."} for part in parts
    ):
        raise ValueError("index path is outside configured corpus categories")
    hub = config.academic_hub_root.resolve()
    for destination in (hub / ".index", hub / ".index" / "chunks"):
        if not destination.resolve().is_relative_to(hub):
            raise ValueError("index write destination escapes configured hub root")
    target = hub.joinpath(*parts)
    if not target.resolve().is_relative_to(hub):
        raise ValueError("index path escapes configured hub root")
    if parts[0] == "academic_notes":
        notes = config.academic_notes_root
        if notes is None or notes.resolve() != (hub / "academic_notes").resolve():
            raise ValueError("configured notes checkout differs from the indexer's source path")
    return parts[1], target


def _preflight(config: ScanConfig, finding: dict) -> tuple[str, str, Path, str]:
    if finding.get("kind") != _CHUNK_KIND or finding.get("root") != "academic-hub-index":
        raise ValueError("finding is not an index chunk repair")
    if finding.get("cost_category") != "paid_api":
        raise ValueError("accepted cost category differs from chunk adapter")
    if finding.get("suggested_action") != "rebuild passage chunks":
        raise ValueError("accepted action parameters differ from chunk adapter")
    if finding.get("expected_output") is not None:
        raise ValueError("chunk finding has an unexpected output destination")
    course, source = _target(config, str(finding.get("path", "")))
    chunks_path = config.academic_hub_root / ".index" / "chunks" / f"{course}.json"
    if not chunks_path.resolve().is_relative_to(config.academic_hub_root.resolve()):
        raise ValueError("chunk shard escapes configured hub root")
    if not source.is_file():
        raise ValueError("indexed source is unavailable")
    cards = [card for card in load_shard(str(config.academic_hub_root), course)
             if not card.get("orphaned") and card.get("path", "").replace("\\", "/") == finding["path"]]
    if len(cards) != 1:
        raise ValueError("index path does not identify exactly one live card")
    card = cards[0]
    file_id = card.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        raise ValueError("card has no file_id")
    if sum(item.get("file_id") == file_id for item in load_shard(str(config.academic_hub_root), course)) != 1:
        raise ValueError("file_id does not identify exactly one card")
    audit = audit_markdown_index(config.academic_hub_root,
                                 [MarkdownIndexTarget(source, finding["path"])],
                                 max_hash_bytes=config.max_hash_bytes)
    if not audit.complete or len(audit.records) != 1:
        raise ValueError("read-only index audit is incomplete")
    record = audit.records[0]
    if record.content_hash != finding.get("fingerprint"):
        raise StaleApproval("source content changed after approval")
    if record.card_status != "current":
        raise ValueError(f"card_status={record.card_status}; reconcile card before chunking")
    if not card.get("embedding") or card.get("needs_indexing"):
        raise ValueError("card has no usable embedding")
    if record.chunks_status not in {"missing_chunks", "stale_chunks"}:
        raise ValueError(f"chunks_status={record.chunks_status}; rescan before applying")
    return course, file_id, source, record.chunks_status


class StaleApproval(ValueError):
    pass


def apply_accepted(
    config: ScanConfig, store: StateStore, *,
    runner: Callable = subprocess.run,
) -> list[dict]:
    """Apply accepted findings one by one; never repair unsupported categories."""
    report = scan(config)
    if not report.complete:
        raise StateError("cannot apply from an incomplete corpus scan")
    current = {StateStore.finding_id(finding): finding for finding in report.findings}
    store.refresh(report.findings)
    outcomes: list[dict] = []
    for entry in store.accepted():
        finding_id = entry["finding_id"]
        finding = entry["finding"]
        fingerprint = finding.get("fingerprint")
        if finding_id not in current:
            continue
        detail: dict = {"started_at": datetime.now(timezone.utc).isoformat()}
        status = "blocked"
        try:
            if finding.get("kind") != _CHUNK_KIND:
                detail["reason"] = _blocked_reason(str(finding.get("kind")))
            else:
                try:
                    course, file_id, _, _ = _preflight(config, finding)
                except StaleApproval as exc:
                    status, detail["reason"] = "pending_review", str(exc)
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    detail["reason"] = str(exc)
                else:
                    command = [sys.executable, "-m", "core.indexer.index_search",
                               "--root", str(config.academic_hub_root.resolve()), "chunk",
                               "--course", course, "--file-id", file_id, "--json"]
                    detail["command"] = command
                    try:
                        with corpus_write_lock([config.academic_hub_root], "corpus-health apply: index chunk") as lease:
                            # Recheck after acquiring the writer lease, immediately before execution.
                            _preflight(config, finding)
                            completed = runner(command, cwd=_PACKAGE_ROOT, env=lease.child_env(),
                                               text=True, capture_output=True, check=False, timeout=3600)
                            detail["exit_code"] = completed.returncode
                            detail["stdout"] = _redact(completed.stdout or "")
                            detail["stderr"] = _redact(completed.stderr or "")
                            if completed.returncode != 0:
                                raise RuntimeError("chunk command exited unsuccessfully")
                            result = json.loads(completed.stdout)
                            if result.get("file_id") != file_id or result.get("matched") is not True or result.get("failed"):
                                raise RuntimeError("chunk command did not confirm the exact card")
                            # Audit while still holding the lease so another writer cannot
                            # change the index between command completion and verification.
                            _preflight_after(config, finding, file_id)
                        status = "applied"
                    except StaleApproval as exc:
                        status, detail["reason"] = "pending_review", str(exc)
                    except (CorpusWriteLockError, OSError, ValueError, RuntimeError,
                            subprocess.TimeoutExpired, KeyError) as exc:
                        status, detail["reason"] = "failed", _redact(str(exc))
        except Exception as exc:
            status, detail["reason"] = "failed", _redact(str(exc))
        detail["finished_at"] = datetime.now(timezone.utc).isoformat()
        store.record_action(finding_id, fingerprint, status, detail)
        outcomes.append({"finding_id": finding_id, "kind": finding.get("kind"),
                         "status": status, **detail})
    store.record_run({"command": "apply", "actions": outcomes})
    return outcomes


def _preflight_after(config: ScanConfig, finding: dict, file_id: str) -> None:
    course, source = _target(config, finding["path"])
    cards = [card for card in load_shard(str(config.academic_hub_root), course)
             if card.get("file_id") == file_id and card.get("path") == finding["path"]]
    if len(cards) != 1:
        raise RuntimeError("card identity changed during chunk repair")
    audit = audit_markdown_index(config.academic_hub_root,
                                 [MarkdownIndexTarget(source, finding["path"])],
                                 max_hash_bytes=config.max_hash_bytes)
    if not audit.complete or len(audit.records) != 1:
        raise RuntimeError("post-run index audit is incomplete")
    record = audit.records[0]
    if record.content_hash != finding.get("fingerprint") or record.card_status != "current" or record.chunks_status != "current":
        raise RuntimeError(f"post-run index state is card={record.card_status}, chunks={record.chunks_status}")
