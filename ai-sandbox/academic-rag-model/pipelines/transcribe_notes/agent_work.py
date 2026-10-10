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
        try:
            raw = json.load(f)
        except json.JSONDecodeError as err:
            raise ValueError(f"manifest at {path} is not valid JSON: {err}") from err
    try:
        return [ManifestEntry(**entry) for entry in raw]
    except TypeError as err:
        raise ValueError(f"manifest at {path} has an unexpected entry shape: {err}") from err


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


from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.transcribe_notes import (
    _ACCUMULATION_WINDOW,
    build_accumulated_context,
    build_transcription_prompt,
    extract_page_text,
    load_json_cache,
    render_page_to_image_bytes,
    resolve_output_dir,
)

_AGENT_TIER3_BATCH_SIZE = 6

_AGENT_OUTPUT_HEADER = "## Agent output"


def render_task_card(
    doc_dir: str, task_id: str, tier: str, pages: list[int],
    page_prompts: dict[int, str], image_paths: dict[int, str], note: str | None = None,
) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    lines = [f"# {task_id} ({tier}, pages {pages[0]}-{pages[-1]})", ""]
    if note:
        lines += [note, ""]
    for page in pages:
        lines += [f"## Page {page}", "", f"Image: `{image_paths[page]}`", "", page_prompts[page], ""]
    lines += [
        "## Expected output",
        "",
        "One section per page above, in order, using this exact format:",
        "",
        "```",
        "--- PAGE <number> ---",
        "<transcribed markdown for that page>",
        "```",
        "",
        _AGENT_OUTPUT_HEADER,
        "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_task_card_output(doc_dir: str, task_id: str) -> str | None:
    card_path = os.path.join(doc_dir, f"{task_id}.md")
    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find(_AGENT_OUTPUT_HEADER)
    if idx == -1:
        return None
    output = content[idx + len(_AGENT_OUTPUT_HEADER):].strip()
    return output or None


class AgentDriver:
    """TranscriptionDriver that writes task cards instead of calling
    Gemini. One instance is reused across every document in a collect
    run; `last_doc_slug` records the slug used for the most recent
    call, for callers (and tests) that need to locate that document's
    work directory afterward."""

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

    def _doc_dir(self, pdf_path: str) -> tuple[str, str]:
        file_id = compute_file_id(pdf_path)
        doc_slug = doc_slug_for(pdf_path, file_id)
        self.last_doc_slug = doc_slug
        doc_dir = doc_work_dir(self.hub_root, self.run_id, doc_slug)
        if doc_slug not in self._task_counters:
            # A fresh AgentDriver instance (submit's auto-stage, or a
            # second --collect with the same --run-id) must continue
            # numbering from whatever this document's manifest already
            # has, not restart at task-0001 and overwrite an existing
            # card (final review, finding C2).
            max_n = 0
            for entry in load_manifest(doc_dir):
                try:
                    max_n = max(max_n, int(entry.task_id.rsplit("-", 1)[1]))
                except (IndexError, ValueError):
                    continue
            self._task_counters[doc_slug] = max_n
        return doc_dir, doc_slug

    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        doc_dir, _ = self._doc_dir(pdf_path)
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.pages == list(batch):
                # Already staged (and not yet submitted) -- a re-collect
                # must not overwrite the agent's in-progress card.
                raise AgentPending()
        task_id = self._next_task_id(self.last_doc_slug)
        image_dir = os.path.join(doc_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        image_paths = {}
        for page in batch:
            image_bytes = render_page_to_image_bytes(pdf_path, page - 1, dpi=150)
            rel_path = os.path.join("images", f"page-{page:04d}.png")
            with open(os.path.join(doc_dir, rel_path), "wb") as f:
                f.write(image_bytes)
            image_paths[page] = rel_path
        page_prompts = {page: prompt for page in batch}  # one shared batch prompt, same for every page in it
        render_task_card(doc_dir, task_id, "batch", batch, page_prompts, image_paths)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="batch", pages=list(batch), status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        doc_dir, _ = self._doc_dir(pdf_path)
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "tier3" and entry.pages and entry.pages[0] == page_num:
                # Already staged (and not yet submitted) -- same reason as
                # transcribe_batch above.
                raise AgentPending()
        task_id = self._next_task_id(self.last_doc_slug)
        last_page = min(page_num + _AGENT_TIER3_BATCH_SIZE - 1, total_pages)
        pages = list(range(page_num, last_page + 1))

        image_dir = os.path.join(doc_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        image_paths = {}
        page_prompts = {}
        for page in pages:
            page_image_bytes = image_bytes if page == page_num else render_page_to_image_bytes(
                pdf_path, page - 1, dpi=200,
            )
            rel_path = os.path.join("images", f"page-{page:04d}.png")
            with open(os.path.join(doc_dir, rel_path), "wb") as f:
                f.write(page_image_bytes)
            image_paths[page] = rel_path
            if page == page_num:
                # Only the card's first page gets real prior-page context,
                # from already-submitted cache entries -- the prompt passed
                # in already has that context baked in (built by process_pdf).
                page_prompts[page] = prompt
            else:
                hint_text = extract_page_text(pdf_path, page - 1)
                page_prompts[page] = build_transcription_prompt(
                    accumulated_context="", hint_text=hint_text, page_number=page,
                    total_pages=total_pages, hint_is_high_confidence=False,
                )

        note = (
            "Strict page order within this card: only Page "
            f"{page_num} above has real prior-page context supplied. For "
            "every later page in this card, carry forward YOUR OWN "
            "transcription of this card's earlier pages as continuity "
            "context -- do not transcribe each page in isolation."
        ) if len(pages) > 1 else None

        render_task_card(doc_dir, task_id, "tier3", pages, page_prompts, image_paths, note=note)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="tier3", pages=pages, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()
