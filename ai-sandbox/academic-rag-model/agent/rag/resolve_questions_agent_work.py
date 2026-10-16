# agent/rag/resolve_questions_agent_work.py
"""
QuestionResolverAgentDriver: writes task cards for resolve_questions.py's two
generative stages (key-term extraction, answer generation) instead of
calling Gemini. Reuses pipelines.transcribe_notes.agent_work's generic
run-directory layout, manifest, and worklist primitives (none of them are
PDF-specific). The shared ManifestEntry.pages: list[int] field holds this
driver's qid strings instead -- a type-hint mismatch, not a runtime one
(dataclasses don't enforce field types); see the plan header for why this
was accepted over forking the manifest module. See docs/superpowers/specs/
agent/rag/2026-10-16-question-resolver-agent-driver-design.md.
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

_OUTPUT_HEADER = "## Agent output"


def render_keyterms_card(doc_dir: str, task_id: str, missing: list[tuple[str, str]]) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    qids = [m[0] for m in missing]
    lines = [f"# {task_id} (key terms, {len(qids)} question(s))", ""]
    for qid, prompt in missing:
        lines += [f"## {qid}", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per question above, in order, using this exact format:", "",
        "```", "--- KEYTERMS <qid> ---", "<comma-separated key terms, or nothing if none apply>", "```", "",
        _OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render_answers_card(doc_dir: str, task_id: str, missing: list[tuple[str, str]]) -> None:
    os.makedirs(doc_dir, exist_ok=True)
    qids = [m[0] for m in missing]
    lines = [f"# {task_id} (answers, {len(qids)} question(s))", ""]
    for qid, prompt in missing:
        lines += [f"## {qid}", "", prompt, ""]
    lines += [
        "## Expected output", "",
        "One section per question above, in order, using this exact format:", "",
        "```", "--- ANSWER <qid> ---", "<the explanation markdown for that question>", "```", "",
        _OUTPUT_HEADER, "",
    ]
    with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_card_output(doc_dir: str, task_id: str) -> str | None:
    card_path = os.path.join(doc_dir, f"{task_id}.md")
    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find(_OUTPUT_HEADER)
    if idx == -1:
        return None
    output = content[idx + len(_OUTPUT_HEADER):].strip()
    return output or None


class QuestionResolverAgentDriver:
    """QuestionResolverDriver that writes task cards instead of calling
    Gemini. One instance is reused across every note in a collect run;
    `last_doc_slug` records the slug used for the most recent call, same
    convention as the PDF and Excalidraw agent drivers."""

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

    def _doc_dir(self, raw_path: str) -> str:
        file_id = compute_file_id(raw_path)
        doc_slug = doc_slug_for(raw_path, file_id)
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

    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str:
        raise AgentPending()  # collect_mode always calls stage_key_terms instead; defensive only

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str:
        raise AgentPending()  # collect_mode always calls stage_answers instead; defensive only

    def stage_key_terms(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        doc_dir = self._doc_dir(note_key)
        qids = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "keyterms" and entry.pages == qids:
                raise AgentPending()  # already staged, not yet submitted -- don't overwrite
        task_id = self._next_task_id(self.last_doc_slug)
        render_keyterms_card(doc_dir, task_id, missing)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="keyterms", pages=qids, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()

    def stage_answers(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        doc_dir = self._doc_dir(note_key)
        qids = [m[0] for m in missing]
        for entry in load_manifest(doc_dir):
            if entry.status != "submitted" and entry.tier == "answers" and entry.pages == qids:
                raise AgentPending()
        task_id = self._next_task_id(self.last_doc_slug)
        render_answers_card(doc_dir, task_id, missing)
        entries = load_manifest(doc_dir)
        entries.append(ManifestEntry(task_id=task_id, tier="answers", pages=qids, status="pending"))
        save_manifest(doc_dir, entries)
        render_worklist(doc_dir, entries)
        raise AgentPending()
