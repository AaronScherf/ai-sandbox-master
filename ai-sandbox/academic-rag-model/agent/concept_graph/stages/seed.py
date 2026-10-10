"""Stage seed: propose the course outline (sections) and a skeleton of concept nodes from the hub's files.

Seed is for starting a graph. It never edits anything that exists; the owner edits the skeleton before `fill`."""
from __future__ import annotations

import re
from pathlib import Path

from ..ipguard import check_prose
from ..schema import SLUG
from ..sources import Passage, classify_passage
from ..store import GraphStore
from ..tasks import Task
from .common import passage_texts, with_ids

STAGE = "seed"
ALLOWED = {"topics", "sections", "nodes"}
SECTION_KEYS = {"id", "title", "order", "state", "lectures", "syllabus_ref"}
NODE_KEYS = {"id", "name", "kind", "section", "topic", "gist"}
STATES = ("taught", "in_progress", "planned")
_SLUG = re.compile(SLUG)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\s*\n", re.DOTALL)
_PAGE_MARK = re.compile(r"<!--.*?-->")
_PRIVATE_LINE = re.compile(r"(?i)(e-?mail|@|https?://|office hours|professor:|teaching assistant|recitation|website|courseworks|classes:)")


def _clean_syllabus(text: str) -> str:
    """The syllabus text minus file metadata and contact details (names, emails, hours, links)."""
    text = _FRONTMATTER.sub("", text.replace("\r\n", "\n"), count=1)
    text = _PAGE_MARK.sub("", text)
    kept = [ln for ln in text.splitlines() if not _PRIVATE_LINE.search(ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


INSTRUCTIONS = """\
Propose the outline of this course as a concept graph skeleton, using only the course materials listed below.

Produce:
- `sections`: the course in teaching order. Each has an `id` (a slug such as s01-binary-relations), a `title`, a numeric
  `order` (unique; 1, 2, 3 ...; use fractions to insert later), and a `state`: taught (lecture dates exist for it),
  in_progress, or planned (in the syllabus or textbook but not yet taught). Add `lectures` (ISO dates) where known.
- `nodes`: the key concepts, definitions, properties, axioms and theorems of each section (roughly 5 to 15 per
  section). Each has an `id` (slug), a `name`, a `kind` from the vocabulary, its `section`, a `topic`, and an optional
  one-line `gist` in your own words.
- `topics`: any new thematic topics you use (the existing ones are listed).

Rules: use slugs (lowercase letters, digits, hyphens) for ids; do not reuse an existing id; each node's `kind` and
`topic` must come from the vocabulary or from the `topics` you add; do not include names of people; do not copy
sentences from the materials (8 or more consecutive shared words in a `gist` is rejected). Prefer fewer, well-chosen
concepts over exhaustive lists: a person will review this skeleton before anything is written about each node.

Result: one YAML mapping with keys topics (optional), sections, nodes.
"""


def _title(file_stem: str) -> str:
    text = re.sub(r"^\d+_", "", file_stem).replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def outline_context(hub_root: str, course: str, *, max_chars: int = 12000) -> tuple[str, list[Passage]]:
    """Describe the course from files on disk only (no model, no embedding).

    The syllabus excerpt (cleaned of contact details) and each textbook's chapter titles become offered passages;
    the context text carries the lecture dates and slide-set titles and points to the passages."""
    base = Path(hub_root) / "academic_notes" / course
    lines: list[str] = []
    passages: list[Passage] = []

    seen_text: set[str] = set()
    for f in sorted((base / "syllabus" / "processed_outputs").glob("*.md")):
        text = _clean_syllabus(f.read_text(encoding="utf-8", errors="ignore"))[:3000].strip()
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        source, ref = classify_passage(str(f))
        passages.append(Passage(id="", source=source, ref=ref, text=text, path=str(f)))

    for chapters in sorted((base / "textbooks" / "processed_outputs").glob("*/chapters")):
        titles = []
        for ch in sorted(chapters.glob("*.rag.md")):
            stem = ch.name[: -len(".rag.md")]
            m = re.match(r"(\d+)_", stem)
            if m and int(m.group(1)) > 0:
                titles.append(f"{int(m.group(1))}. {_title(stem)}")
        if titles:
            source, _ = classify_passage(str(chapters / "x.rag.md"))
            passages.append(Passage(id="", source=source, ref="table of contents", text="\n".join(titles), path=str(chapters)))

    notes = [*(base / "lecture_notes").glob("*.md"), *(base / "lecture_notes" / "processed_outputs").glob("*.md")]
    dates = sorted({m.group(0) for f in notes for m in [_DATE.search(f.name)] if m})
    if dates:
        lines += ["Lecture dates with notes: " + ", ".join(dates), ""]

    def slide_key(f: Path):
        m = re.match(r"(\d+)\.", f.name)
        return (int(m.group(1)) if m else 10_000, f.name)

    slides = []
    for f in sorted((base / "professor_notes" / "processed_outputs").glob("*.md"), key=slide_key):
        title = classify_passage(str(f))[1]
        if "proof" not in f.name.lower() and title not in slides:
            slides.append(title)
    if slides:
        lines += ["Professor slide sets (in course order): " + "; ".join(slides), ""]

    lines += ["The syllabus excerpt and each textbook's table of contents are under 'Offered passages' below."]
    context = "\n".join(lines).strip()
    if len(context) > max_chars:
        context = context[:max_chars] + "\n[context truncated]"
    return context, passages


def make_tasks(store: GraphStore, retriever=None, *, hub_root: str | None = None, course: str | None = None,
               redo: bool = False, **_ignored) -> list[Task]:
    if not hub_root or not course:
        raise ValueError("seed needs --hub-root and --course")
    graph = store.read_all()
    if any(s.state in ("taught", "in_progress") for s in graph.sections) and not redo:
        raise ValueError("the graph already has taught sections; seed is for starting a graph (use --redo to add to it)")
    context, passages = outline_context(hub_root, course)
    existing = [f"- section {s.id} (order {s.order}, {s.state}): {s.title}" for s in graph.sections]
    existing += [f"- node {n.id}" for n in graph.nodes]
    body = "\n".join([
        f"Course: {course}", "",
        "Vocabulary. kinds: " + ", ".join(graph.vocab.kinds), "topics: " + ", ".join(graph.vocab.topics), "",
        "Already in the graph (do not reuse these ids):", *(existing or ["- (nothing yet)"]), "",
        "Course materials:", context or "(no materials found)",
    ])
    return [Task(id="seed", stage=STAGE, subject={"stage": "seed"}, instructions=INSTRUCTIONS, context=body,
                 passages=with_ids(passages))]


def validate_result(entry: dict, result: dict, store: GraphStore) -> list[str]:
    problems = []
    unknown = sorted(set(result) - ALLOWED)
    if unknown:
        problems.append(f"unknown key(s) {unknown}; allowed: {sorted(ALLOWED)}")
    graph = store.read_all()
    topics, sections, nodes = result.get("topics") or [], result.get("sections") or [], result.get("nodes") or []
    if not isinstance(topics, list) or not isinstance(sections, list) or not isinstance(nodes, list):
        return problems + ["topics, sections and nodes must each be a list"]
    if not sections and not nodes:
        return problems + ["the result proposes nothing: give at least one section or node"]

    new_topics = []
    for t in topics:
        if not isinstance(t, str) or not _SLUG.match(t):
            problems.append(f"topic {t!r}: must be a slug (lowercase letters, digits, hyphens)")
        else:
            new_topics.append(t)
    known_topics = set(graph.vocab.topics) | set(new_topics)

    taken_sections = {s.id for s in graph.sections}
    taken_orders = {s.order for s in graph.sections}
    new_sections: dict[str, dict] = {}
    for i, s in enumerate(sections, 1):
        tag = f"section {i}"
        if not isinstance(s, dict):
            problems.append(f"{tag}: must be a mapping")
            continue
        extra = sorted(set(s) - SECTION_KEYS)
        if extra:
            problems.append(f"{tag}: unknown key(s) {extra}; allowed: {sorted(SECTION_KEYS)}")
        sid = s.get("id")
        if not isinstance(sid, str) or not _SLUG.match(sid):
            problems.append(f"{tag}: id {sid!r} must be a slug (lowercase letters, digits, hyphens)")
        elif sid in taken_sections:
            problems.append(f"{tag}: id {sid!r} already exists")
        elif sid in new_sections:
            problems.append(f"{tag}: id {sid!r} appears twice")
        else:
            new_sections[sid] = s
        if not isinstance(s.get("title"), str) or not s["title"].strip():
            problems.append(f"{tag}: title is required")
        order = s.get("order")
        if isinstance(order, bool) or not isinstance(order, (int, float)):
            problems.append(f"{tag}: order must be a number")
        elif order in taken_orders:
            problems.append(f"{tag}: order {order} is already used by another section")
        else:
            taken_orders.add(order)
        if s.get("state") not in STATES:
            problems.append(f"{tag}: state must be one of {', '.join(STATES)}")
        lectures = s.get("lectures", [])
        if not isinstance(lectures, list) or not all(isinstance(d, str) and _DATE.fullmatch(d) for d in lectures):
            problems.append(f"{tag}: lectures must be a list of ISO dates (YYYY-MM-DD)")

    section_ids = taken_sections | set(new_sections)
    taken_nodes = {n.id for n in graph.nodes}
    seen_nodes: set[str] = set()
    for i, n in enumerate(nodes, 1):
        tag = f"node {i}"
        if not isinstance(n, dict):
            problems.append(f"{tag}: must be a mapping")
            continue
        extra = sorted(set(n) - NODE_KEYS)
        if extra:
            problems.append(f"{tag}: unknown key(s) {extra}; allowed: {sorted(NODE_KEYS)}")
        nid = n.get("id")
        if not isinstance(nid, str) or not _SLUG.match(nid):
            problems.append(f"{tag}: id {nid!r} must be a slug (lowercase letters, digits, hyphens)")
        elif nid in taken_nodes:
            problems.append(f"{tag}: id {nid!r} already exists")
        elif nid in seen_nodes:
            problems.append(f"{tag}: id {nid!r} appears twice")
        else:
            seen_nodes.add(nid)
        if not isinstance(n.get("name"), str) or not n["name"].strip():
            problems.append(f"{tag}: name is required")
        if n.get("kind") not in graph.vocab.kinds:
            problems.append(f"{tag}: kind {n.get('kind')!r} is not in the vocabulary ({', '.join(graph.vocab.kinds)})")
        if n.get("section") not in section_ids:
            problems.append(f"{tag}: section {n.get('section')!r} is not an existing or proposed section")
        if n.get("topic") not in known_topics:
            problems.append(f"{tag}: topic {n.get('topic')!r} is not in the vocabulary; list it under `topics` to add it")
        gist = n.get("gist")
        if gist is not None:
            if not isinstance(gist, str) or "\n" in gist.strip() or len(gist.strip()) > 160:
                problems.append(f"{tag}: gist must be one line of at most 160 characters")
            else:
                problems += [f"{tag} {m}" for m in check_prose({"gist": gist}, passage_texts(entry))]
    return problems


def apply_result(store: GraphStore, entry: dict, result: dict, provenance: dict) -> str | None:
    graph = store.read_all()
    new_topics = [t for t in (result.get("topics") or []) if t not in graph.vocab.topics]
    if new_topics:
        store.add_vocab(topics=new_topics)
    sections = [{"id": s["id"], "title": s["title"].strip(), "order": s["order"], "state": s["state"],
                 "lectures": list(s.get("lectures") or []), "syllabus_ref": s.get("syllabus_ref")}
                for s in (result.get("sections") or [])]
    if sections:
        store.add_sections(sections)
    by_section: dict[str, list[dict]] = {}
    for n in result.get("nodes") or []:
        by_section.setdefault(n["section"], []).append({
            "id": n["id"], "name": n["name"].strip(), "kind": n["kind"], "section": n["section"], "topic": n["topic"],
            "gist": (n.get("gist") or "").strip() or None, "status": "proposed", "provenance": provenance})
    for section_id, items in by_section.items():
        store.add_nodes(section_id, items)
    return None
