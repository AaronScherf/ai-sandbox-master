# pipelines/transcribe_notes/agent_work.py
"""
Collect/submit support for transcribe_notes.py's agent-driven mode: run
directory layout, the machine-readable manifest, the human-readable
worklist, task cards, and AgentDriver (added in a later task of the same
plan). See docs/superpowers/specs/transcribe_notes/
2026-10-09-agent-driven-transcription-design.md.

All paths here live under <hub_root>/.agent_work/ -- never under
academic_notes/ or academic_resources/, and .agent_work/ is gitignored
(root .gitignore) and pruned by every discovery path that walks the
filesystem by dot-directory name.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass

from core.indexer.index_card import compute_file_id


def agent_work_dir(hub_root: str, run_id: str) -> str:
    return os.path.join(hub_root, ".agent_work", run_id)


def doc_work_dir(hub_root: str, run_id: str, doc_slug: str) -> str:
    return os.path.join(agent_work_dir(hub_root, run_id), doc_slug)


_SLUG_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def doc_slug_for(pdf_path: str, file_id: str) -> str:
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    safe_base = _SLUG_UNSAFE_RE.sub("_", base_name).strip("_") or "doc"
    return f"{safe_base}--{file_id[:8]}"


@dataclass
class ManifestEntry:
    task_id: str
    tier: str
    pages: list[int]
    status: str  # "pending" | "filled" | "submitted" | "bounced"
    bounce_reason: str | None = None


def _manifest_path(doc_dir: str) -> str:
    return os.path.join(doc_dir, "manifest.json")


def load_manifest(doc_dir: str) -> list[ManifestEntry]:
    path = _manifest_path(doc_dir)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [ManifestEntry(**entry) for entry in raw]


def save_manifest(doc_dir: str, entries: list[ManifestEntry]) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    with open(_manifest_path(doc_dir), "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in entries], f, indent=2)


def render_worklist(doc_dir: str, entries: list[ManifestEntry]) -> None:
    lines = ["# Worklist", "", "| Task | Tier | Pages | Status |", "|---|---|---|---|"]
    for e in entries:
        status = e.status if not e.bounce_reason else f"{e.status}: {e.bounce_reason}"
        page_range = f"{e.pages[0]}-{e.pages[-1]}" if len(e.pages) > 1 else str(e.pages[0])
        lines.append(f"| {e.task_id} | {e.tier} | {page_range} | {status} |")
    with open(os.path.join(doc_dir, "worklist.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def dedupe_by_file_id(pdf_paths: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Groups byte-identical PDFs (same compute_file_id) within one
    collect run. find_existing_transcription only matches against
    finished transcriptions elsewhere in the corpus -- it has nothing to
    match two not-yet-transcribed duplicates against in the same run, so
    this is collect's own first pass before any cards are written."""
    by_id: dict[str, list[str]] = {}
    for path in pdf_paths:
        file_id = compute_file_id(path)
        by_id.setdefault(file_id, []).append(path)
    canonical = [paths[0] for paths in by_id.values()]
    duplicates_of = {paths[0]: paths[1:] for paths in by_id.values() if len(paths) > 1}
    return canonical, duplicates_of
