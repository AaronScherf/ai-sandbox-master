# pipelines/transcribe_notes/excalidraw_agent_work.py
"""
ExcalidrawAgentDriver: writes task cards for transcribe_excalidraw.py's two
generative stages (chunk transcription, segment expansion) instead of
calling Gemini. Reuses agent_work.py's generic run-directory layout,
manifest, and worklist primitives (none of them are PDF-specific). See
docs/superpowers/specs/transcribe_notes/2026-10-15-excalidraw-agent-driver-design.md.
"""
from __future__ import annotations

import os

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import (
    ManifestEntry,
    doc_slug_for,
    doc_work_dir,
    load_manifest,
    render_worklist,
    save_manifest,
)
from core.indexer.index_card import compute_file_id

_CHUNK_OUTPUT_HEADER = "## Agent output"


def render_chunk_card(
    doc_dir: str, task_id: str, missing: list[tuple[int, str, bytes]], total_chunks: int,
) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    image_dir = os.path.join(doc_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    indices = [m[0] for m in missing]
    lines = [f"# {task_id} (chunks, {indices[0]}-{indices[-1]} of {total_chunks - 1})", ""]
    if len(missing) > 1:
        lines += [
            "Strict chunk order within this card: only the first chunk below has real "
            "prior-chunk context supplied. For every later chunk in this card, carry forward "
            "YOUR OWN transcription of this card's earlier chunks as continuity context.",
            "",
        ]
    for chunk_index, prompt, image_bytes in missing:
        rel_path = os.path.join("images", f"chunk-{chunk_index:04d}.png")
        with open(os.path.join(doc_dir, rel_path), "wb") as f:
            f.write(image_bytes)
        lines += [f"## Chunk {chunk_index}", "", f"Image: `{rel_path}`", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per chunk above, in order, using this exact format:", "",
        "```", "--- CHUNK <number> ---", "<transcribed markdown for that chunk>", "```", "",
        _CHUNK_OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render_expansion_card(doc_dir: str, task_id: str, missing: list[tuple[int, str]], total_segments: int) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    indices = [m[0] for m in missing]
    lines = [f"# {task_id} (expansion segments, {indices[0]}-{indices[-1]} of {total_segments - 1})", ""]
    for segment_index, prompt in missing:
        lines += [f"## Segment {segment_index}", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per segment above, in order, using this exact format:", "",
        "```", "--- SEGMENT <number> ---", "<expanded markdown for that segment>", "```", "",
        _CHUNK_OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_card_output(doc_dir: str, task_id: str) -> str | None:
    card_path = os.path.join(doc_dir, f"{task_id}.md")
    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find(_CHUNK_OUTPUT_HEADER)
    if idx == -1:
        return None
    output = content[idx + len(_CHUNK_OUTPUT_HEADER):].strip()
    return output or None


class ExcalidrawAgentDriver:
    """ExcalidrawDriver that writes task cards instead of calling Gemini.
    One instance is reused across every note in a collect run;
    `last_doc_slug` records the slug used for the most recent call, same
    convention as agent_work.AgentDriver."""

    def __init__(self, hub_root: str, run_id: str, agent_name: str = "antigravity"):
        self.hub_root = hub_root
        self.run_id = run_id
        self.agent_name = agent_name
        self._task_counters: dict[str, int] = {}
        self.last_doc_slug: str | None = None

    def _next_task_id(self, doc_slug: str) -> str:
        n = self._task_counters.get(doc_slug, 0) + 1
        self._task_counters[doc_slug] = n
        return f"task-{n:04d}"

    def _doc_dir(self, excalidraw_md_path: str) -> str:
        file_id = compute_file_id(excalidraw_md_path)
        doc_slug = doc_slug_for(excalidraw_md_path, file_id)
        self.last_doc_slug = doc_slug
        doc_dir = doc_work_dir(self.hub_root, self.run_id, doc_slug)
        if doc_slug not in self._task_counters:
            max_n = 0
            for entry in load_manifest(doc_dir):
                try:
                    max_n = max(max_n, int(entry.task_id.rsplit("-", 1)[1]))
                except (IndexError, ValueError):
                    continue
            self._task_counters[doc_slug] = max_n
        return doc_dir

    def transcribe_chunk(self, excalidraw_md_path, model, chunk_index, total_chunks, prompt, image_bytes) -> str:
        raise AgentPending()  # collect_mode always calls stage_chunks instead; defensive only

    def expand(self, excalidraw_md_path, prompt, segment_index, total_segments) -> str:
        raise AgentPending()  # collect_mode always calls stage_segments instead; defensive only

    def stage_chunks(self, excalidraw_md_path, model, missing, total_chunks) -> dict[int, str]:
        doc_dir = self._doc_dir(excalidraw_md_path)
        indices = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "chunks" and entry.pages == indices:
                raise AgentPending()  # already staged, not yet submitted -- don't overwrite
        task_id = self._next_task_id(self.last_doc_slug)
        render_chunk_card(doc_dir, task_id, missing, total_chunks)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="chunks", pages=indices, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()

    def stage_segments(self, excalidraw_md_path, missing, total_segments) -> dict[int, str]:
        doc_dir = self._doc_dir(excalidraw_md_path)
        indices = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "segments" and entry.pages == indices:
                raise AgentPending()
        task_id = self._next_task_id(self.last_doc_slug)
        render_expansion_card(doc_dir, task_id, missing, total_segments)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="segments", pages=indices, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()
