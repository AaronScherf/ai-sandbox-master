"""Exact, reviewed marker migration for the canonical outer-repo tracker."""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from tools.git_workflow import run_git
from tools.project_steering.parser import parse_tracker
from tools.project_steering.report import _write_atomic


TRACKER_RELATIVE = Path("ai-sandbox/academic-rag-model/docs/trackers/academic_hub_to_do.md")
MARKER = re.compile(r"<!-- TODO-(\d{4,}) -->")


@dataclass(frozen=True)
class IdPreview:
    source_sha256: str
    diff: str
    assigned: int
    needs_id: tuple[int, ...]
    output: str


def preview_ids(source: str) -> IdPreview:
    parsed = parse_tracker(source)
    lines = source.splitlines(keepends=True)
    updated = lines.copy()
    next_id = max((int(match.group(1)) for match in MARKER.finditer(source)), default=0) + 1
    needs_id = {item.first_line for item in parsed.warnings if item.kind != "needs_id"}
    assigned = 0
    for task in parsed.tasks:
        if not task.provisional or task.first_line in needs_id:
            continue
        index = task.first_line - 1
        line = lines[index]
        if not line.startswith("- ") or "<!--" in line[2:52]:
            needs_id.add(task.first_line)
            continue
        updated[index] = f"- <!-- TODO-{next_id:04d} --> " + line[2:]
        next_id += 1
        assigned += 1
    output = "".join(updated)
    diff = "".join(difflib.unified_diff(lines, updated, fromfile="tracker", tofile="tracker+ids"))
    return IdPreview(hashlib.sha256(source.encode("utf-8")).hexdigest(), diff, assigned,
                     tuple(sorted(needs_id)), output)


def _verify_tracker_path(path: Path) -> None:
    root = Path(run_git(["rev-parse", "--show-toplevel"], path.parent).strip()).resolve()
    if path.resolve() != (root / TRACKER_RELATIVE).resolve():
        raise ValueError(f"apply-ids requires the outer-monorepo tracker: {root / TRACKER_RELATIVE}")
    tracked = run_git(["ls-files", "--error-unmatch", str(TRACKER_RELATIVE).replace("\\", "/")], root)
    if not tracked.strip():
        raise ValueError("tracker is not tracked in the outer monorepo")


def apply_ids(path: Path, expected_sha256: str) -> IdPreview:
    """Reject concurrent edits and replace only exact lines from one preview."""
    _verify_tracker_path(path)
    source_bytes = path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != expected_sha256:
        raise ValueError("stale tracker; run preview-ids again")
    source = source_bytes.decode("utf-8")
    preview = preview_ids(source)
    if preview.needs_id:
        raise ValueError(f"unresolved needs_id at lines {preview.needs_id}; review before migration")
    if preview.assigned == 0:
        return preview
    if path.read_bytes() != source_bytes:
        raise ValueError("stale tracker; run preview-ids again")
    reparsed = parse_tracker(preview.output)
    if reparsed.warnings or any(task.provisional for task in reparsed.tasks):
        raise ValueError("reparse failed; tracker unchanged")
    # The tracked file is edited only by an explicitly invoked migration in an assigned worktree.
    _write_atomic(path, preview.output)
    if path.read_bytes().decode("utf-8") != preview.output:
        raise OSError("post-run audit failed: tracker bytes differ")
    return preview
