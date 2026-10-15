"""Draft one cohesive summary per section: what the group of concepts is about and how they fit together."""
from __future__ import annotations

from ..ipguard import check_meta, check_prose
from ..schema import member_hash
from ..store import GraphStore
from ..tasks import Task
from .common import passage_texts, with_ids

STAGE = "summary"
ALLOWED = {"summary"}
MAX_WORDS = 110
MAX_CHARS = 700

INSTRUCTIONS = """\
Write one short, cohesive summary of this course section for a graduate student: what the group of concepts is about,
how the main ideas fit together, and why the section matters for what comes next. Put the YAML under `## Result`:

  summary: "..."

Rules:
- One paragraph of at most 110 words, in your OWN words. A run of 8 or more consecutive words shared with a passage is
  rejected.
- Describe the ideas themselves. Never mention the passages, the sources, the lectures, or what they do or do not cover.
- Do not list the concepts one by one; explain how they relate. Close every $ in LaTeX. Quote the value."""


def make_tasks(store: GraphStore, retriever, *, section: str | None = None, redo: bool = False, top_k: int = 6,
               **_ignored) -> list[Task]:
    graph = store.read_all()
    tasks = []
    for s in sorted(graph.sections, key=lambda s: s.order):
        if section and s.id != section:
            continue
        members = [n for n in graph.nodes if n.section == s.id]
        if not members or s.state == "planned":
            continue
        current = (s.summary or "").strip() and s.summary_hash == member_hash([n.id for n in members])
        if current and not redo:
            continue
        lines = [f"Section: {s.title}   (id: {s.id})", f"Short label: {s.short or s.title}", "", "Concepts in this section:"]
        for n in sorted(members, key=lambda n: n.name.lower()):
            lines.append(f"- {n.name} ({n.kind}): {n.gist or '(no one-line summary)'}")
        query = f"{s.title} " + " ".join(n.name for n in members[:12])
        passages = with_ids(retriever.retrieve(query, top_k))
        tasks.append(Task(id=f"summary-{s.id}", stage=STAGE, subject={"section": s.id}, instructions=INSTRUCTIONS,
                          context="\n".join(lines), passages=passages))
    return tasks


def validate_result(entry: dict, result: dict, store: GraphStore) -> list[str]:
    problems = []
    unknown = sorted(set(result) - ALLOWED)
    if unknown:
        problems.append(f"unknown key(s) {unknown}; the result has only `summary`")
    text = result.get("summary")
    if not isinstance(text, str) or not text.strip():
        return problems + ["summary: required"]
    text = text.strip()
    if "\n\n" in text:
        problems.append("summary: must be a single paragraph")
    if len(text.split()) > MAX_WORDS or len(text) > MAX_CHARS:
        problems.append(f"summary: must be at most {MAX_WORDS} words and {MAX_CHARS} characters")
    if text.replace("\\$", "").replace("$$", "").count("$") % 2 == 1:
        problems.append("summary: the math delimiters do not balance (an odd number of $)")
    problems += check_meta({"summary": text})
    problems += check_prose({"summary": text}, passage_texts(entry))
    if not any(s.id == entry["subject"]["section"] for s in store.read_all().sections):
        problems.append("the section no longer exists")
    return problems


def apply_result(store: GraphStore, entry: dict, result: dict, provenance: dict) -> str | None:
    sid = entry["subject"]["section"]
    graph = store.read_all()
    ids = [n.id for n in graph.nodes if n.section == sid]
    store.update_section(sid, {"summary": result["summary"].strip(), "summary_hash": member_hash(ids)})
    return None
