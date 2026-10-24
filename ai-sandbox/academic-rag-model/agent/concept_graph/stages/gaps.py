"""Compare syllabus readings with graph nodes, then submit gaps as reviewer proposals."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from core.agent_tasks.tasks import Passage, Task
from core.course_materials import Catalog, load_catalog
from pydantic import ValidationError

from ..proposals import EdgeProposal, NodeProposal, NAME_MAX, NOTE_MAX
from ..reviews import Decision, ReviewFile, Reviewer, apply_proposals
from ..schema import EDGE_TYPES
from ..store import GraphStore
from .common import with_ids
from .seed import _clean_syllabus

STAGE = "gaps"
_TOPICS = re.compile(r"^\s*#{0,3}\s*topics\s*:?\s*$", re.I)
_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
_SECTION = re.compile(r"^(\d+)\.(\d+)\b")
_NUMBER = re.compile(r"(?<!\d)(\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?)")
_READING_NOTE = re.compile(r"\b\d+(?:\.\d+)?\b")
_BOOK_REFERENCE = re.compile(r"\b([A-Za-z][A-Za-z-]{1,30})\.?\s+(\d+(?:\.\d+)?(?:[-–]\d+(?:\.\d+)?)?)")


def _source(hub: Path, relative: str) -> Path:
    path = (hub / relative).resolve()
    if hub.resolve() not in path.parents or not path.is_file():
        raise ValueError(f"course source is missing or outside the hub: {relative}")
    return path


def _topic_lines(text: str) -> list[str]:
    lines = _clean_syllabus(text).splitlines()
    start = next((i + 1 for i, line in enumerate(lines) if _TOPICS.match(line)), None)
    if start is None:
        raise ValueError("syllabus has no Topics/reading-list section")
    out = []
    for line in lines[start:]:
        if re.match(r"^\s*#{1,3}\s+", line):
            break
        line = line.strip()
        if line and not line.startswith("<!--"):
            out.append(line)
    if not out:
        raise ValueError("syllabus Topics section has no assignments")
    return out


def _readings(line: str, aliases: dict[str, str]) -> list[tuple[str, str, str]]:
    names = sorted(aliases, key=len, reverse=True)
    if not names:
        return []
    label = re.compile(r"(?<![\w])(?:" + "|".join(re.escape(x) for x in names) + r")\.?\s+(?=\d)", re.I)
    hits = list(label.finditer(line))
    found = []
    for i, hit in enumerate(hits):
        book = aliases[hit.group().strip().rstrip(".").casefold()]
        segment = line[hit.end():hits[i + 1].start() if i + 1 < len(hits) else len(line)]
        for part in segment.split(","):
            number = _NUMBER.search(part)
            if number:
                found.append((book, number.group(1).replace(" ", ""), hit.group().strip().rstrip(".")))
    return found


def _expand(number: str) -> list[tuple[int, int | None]]:
    ends = re.split("[-–]", number)
    def pair(value):
        bits = value.split(".")
        return int(bits[0]), int(bits[1]) if len(bits) == 2 else None
    first = pair(ends[0])
    if len(ends) == 1:
        return [first]
    last = pair(ends[1])
    if first[1] is None and last[1] is None and last[0] >= first[0]:
        return [(i, None) for i in range(first[0], last[0] + 1)]
    if first[0] == last[0] and first[1] is not None and last[1] is not None and last[1] >= first[1]:
        return [(first[0], i) for i in range(first[1], last[1] + 1)]
    raise ValueError(f"unsupported reading range {number!r}")


def _headings(text: str) -> tuple[int | None, list[str]]:
    headings = [re.sub(r"<[^>]+>", "", m.group(1)).strip(" *")
                for line in text.splitlines() if (m := _HEADING.match(line))]
    chapter = None
    for title in headings:
        if (match := re.search(r"\bCHAPTER\s+(\d+)\b", title, re.I)):
            chapter = int(match.group(1))
            break
        if (match := re.search(r"(?:^|\s)(\d+)\s*$", title)):
            chapter = int(match.group(1))
            break
    if chapter is None:
        section = next((_SECTION.match(title) for title in headings if _SECTION.match(title)), None)
        chapter = int(section.group(1)) if section else None
    return chapter, headings


def _assigned_headings(headings: list[str], chapter: int, section: int | None) -> list[str]:
    if section is None:
        return headings
    wanted = f"{chapter}.{section}"
    output = []
    active = False
    for heading in headings:
        match = _SECTION.match(heading)
        if match:
            active = f"{match.group(1)}.{match.group(2)}" == wanted
        if active:
            output.append(heading)
    return output


def _toc_heading(text: str, chapter: int, section: int) -> str | None:
    """Recover an assigned title from a book's contents when its extracted section is absent."""
    marker = re.escape(f"{chapter}.{section}")
    match = re.search(r"\*\*" + marker + r"\*\*\s+(.+?)\s+\d+(?=\s|$)", text)
    if match:
        return f"{chapter}.{section} {match.group(1).strip()} [contents only; section text unavailable]"
    return None


def _digest(store: GraphStore, hub_root: str, paths: list[str]) -> str:
    graph = store.read_all()
    config = store.read_seed_config()
    hub = Path(hub_root)
    state = {
        "sources": [(p, hashlib.sha256(_source(hub, p).read_bytes()).hexdigest()) for p in paths],
        "aliases": config.reading_aliases,
        "sections": [(s.id, s.title, s.topic) for s in graph.sections],
        "nodes": [(n.id, n.name, n.kind, n.section, n.topic) for n in graph.nodes],
        "rejected": [(r.kind, r.id) for r in graph.rejected],
        "vocabulary": graph.vocab.model_dump(mode="json"),
    }
    return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def make_tasks(store: GraphStore, retriever=None, *, hub_root: str | None = None, course: str | None = None,
               catalog: Catalog | None = None, **_ignored) -> list[Task]:
    if not hub_root or not course:
        raise ValueError("gaps needs --hub-root and --course")
    catalog = catalog or load_catalog(hub_root, course)
    graph = store.read_all()
    if not graph.sections:
        raise ValueError("gaps needs graph sections; run seed first")
    syllabi = catalog.by_role("syllabus")
    if not syllabi:
        raise ValueError("gaps needs a classified syllabus")
    if any(m.flagged for m in syllabi):
        raise ValueError("resolve flagged syllabus files first: " + ", ".join(m.path for m in syllabi if m.flagged))
    hub = Path(hub_root)
    config = store.read_seed_config()
    books = catalog.book_keys()
    aliases = {key.casefold(): key for key in books}
    for alias, book in config.reading_aliases.items():
        if book not in books:
            raise ValueError(f"reading alias {alias!r} names unknown catalog book {book!r}")
        aliases[alias.casefold()] = book
    topics, assignments, source_paths = [], [], []
    for material in syllabi:
        text = _source(hub, material.path).read_text(encoding="utf-8", errors="ignore")
        lines = _topic_lines(text)
        unknown = sorted({m.group(1) for line in lines for m in _BOOK_REFERENCE.finditer(line)
                          if m.group(1).casefold() not in aliases
                          and ("." in m.group(2) or m.group(1).isupper())})
        if unknown:
            raise ValueError("unmapped syllabus reading label(s): " + ", ".join(unknown) +
                             "; add reading_aliases in config/seed.yaml")
        topics.extend(line for line in lines if line not in topics)
        assignments.extend((line, book, number, label) for line in lines
                           for book, number, label in _readings(line, aliases))
        source_paths.append(material.path)
    if not assignments:
        raise ValueError("syllabus Topics section has no resolved reading assignments; add reading_aliases if needed")
    wanted = {(book, chapter) for _, book, number, _ in assignments for chapter, _ in _expand(number)}
    by_chapter = {}
    contents = {}
    for material in catalog.by_role("textbook"):
        if material.book not in {book for book, _ in wanted}:
            continue
        text = _source(hub, material.path).read_text(encoding="utf-8", errors="ignore")
        if material.stem.startswith("00_") or "front_matter" in material.stem:
            contents[material.book] = (material, text)
            continue
        chapter, heads = _headings(text)
        if chapter is not None and (material.book, chapter) in wanted:
            if material.flagged:
                raise ValueError(f"resolve flagged textbook file first: {material.path}")
            key = (material.book, chapter)
            if key not in by_chapter or material.path.endswith(".rag.md"):
                by_chapter[key] = (material, heads)
    reading_lines, passages, missing = [], [], []
    seen = set()
    for line, book, number, label in assignments:
        for chapter, section in _expand(number):
            key = (book, chapter)
            match = by_chapter.get(key)
            heads = _assigned_headings(match[1], chapter, section) if match else []
            material = match[0] if match else None
            if match and not heads and section is not None and book in contents:
                fallback = _toc_heading(contents[book][1], chapter, section)
                if fallback:
                    if contents[book][0].flagged:
                        raise ValueError(f"resolve flagged textbook file first: {contents[book][0].path}")
                    heads = [fallback]
                    material = contents[book][0]
            if not heads:
                missing.append(f"{label} {chapter}" + (f".{section}" if section is not None else ""))
                continue
            ref = f"{label} {chapter}" + (f".{section}" if section is not None else "")
            if ref in seen:
                continue
            seen.add(ref)
            source_paths.append(material.path)
            reading_lines.append(f"- {ref} ({material.path}): " + "; ".join(heads))
            passages.append(Passage(id="", source=book, ref=ref, text="\n".join(heads), path=str(_source(hub, material.path))))
    if missing:
        raise ValueError("assigned textbook headings not found: " + ", ".join(dict.fromkeys(missing)))
    source_paths = list(dict.fromkeys(source_paths))
    lines = [f"Course: {course}", "", "Syllabus topics and assigned readings:",
             *(f"- {line}" for line in topics), "", "Textbook section headings for those readings:", *reading_lines,
             "", "Current nodes by graph section:"]
    for section in graph.sections:
        names = [n.name for n in graph.nodes if n.section == section.id]
        lines.append(f"- {section.id}: {section.title} (topic: {section.topic or '(none)'})")
        lines.extend(f"  - {name}" for name in names)
        if not names:
            lines.append("  - (zero nodes)")
    lines += ["", "Kinds: " + ", ".join(graph.vocab.kinds), "Topics: " + ", ".join(graph.vocab.topics),
              "Rejected concept ids: " + (", ".join(r.id for r in graph.rejected if r.kind == "node") or "(none)")]
    instructions = ("Compare every assigned syllabus reading with its textbook headings and the current nodes. "
                    "Propose only missing in-scope concepts in existing sections; do not repeat or rename existing "
                    "concepts. Keep technical qualifiers distinct. Each proposal needs a short syllabus reading "
                    "reference in its note. Return YAML keys proposals and edges (both lists; [] means no gaps). "
                    "A concept proposal has name, kind, section, topic, note, and optional connections; a standalone "
                    "edge has source, type, target, condition if required, and note. These are reviewer proposals, "
                    "not verified graph items.")
    return [Task(id="gaps", stage=STAGE, subject={"stage": STAGE, "hub_root": str(hub.resolve()),
                 "sources": source_paths, "digest": _digest(store, hub_root, source_paths)},
                 instructions=instructions, context="\n".join(lines), passages=with_ids(passages))]


def validate_result(entry: dict, result: dict, store: GraphStore) -> list[str]:
    subject = entry.get("subject", {})
    try:
        if _digest(store, subject["hub_root"], subject["sources"]) != subject["digest"]:
            return ["stale gap card: syllabus, textbook, config or graph changed; collect gaps again"]
    except (KeyError, ValueError, FileNotFoundError) as exc:
        return [f"stale gap card: source missing or invalid ({exc}); collect gaps again"]
    if set(result) != {"proposals", "edges"}:
        return ["result needs exactly proposals and edges lists"]
    if not isinstance(result["proposals"], list) or not isinstance(result["edges"], list):
        return ["proposals and edges must be lists"]
    graph = store.read_all()
    sections = {s.id for s in graph.sections}
    problems = []
    for kind, items, model in (("proposal", result["proposals"], NodeProposal),
                               ("edge", result["edges"], EdgeProposal)):
        for index, raw in enumerate(items, 1):
            try:
                item = model.model_validate(raw)
            except ValidationError as exc:
                problems.append(f"{kind} {index}: {exc.errors()[0]['msg']}")
                continue
            if len(item.note) > NOTE_MAX or not _READING_NOTE.search(item.note):
                problems.append(f"{kind} {index}: note needs a syllabus reading reference within {NOTE_MAX} characters")
            if kind == "proposal":
                if len(item.name) > NAME_MAX:
                    problems.append(f"proposal {index}: name exceeds {NAME_MAX} characters")
                if item.kind not in graph.vocab.kinds or item.section not in sections or (item.topic and item.topic not in graph.vocab.topics):
                    problems.append(f"proposal {index}: use an existing kind, section and topic")
            elif item.type not in EDGE_TYPES:
                problems.append(f"edge {index}: unknown type {item.type!r}")
    return problems


def apply_result(store: GraphStore, entry: dict, result: dict, provenance: dict) -> str | None:
    today = dt.date.today().isoformat()
    decisions = ([Decision(action="add_node", proposal=NodeProposal.model_validate(raw))
                  for raw in result["proposals"]] +
                 [Decision(action="add_edge", proposal=EdgeProposal.model_validate(raw)) for raw in result["edges"]])
    review = ReviewFile(schema_version=2, graph_version=entry["subject"]["digest"],
                        reviewer=Reviewer(name=provenance.get("agent") or "ide-agent"),
                        created=today, decisions=decisions)
    report = apply_proposals(store, [review], today)
    store.read_all()  # audit the resulting graph data through the public store interface
    for label, messages in (("applied", report.applied), ("skipped", report.skipped),
                            ("conflict", report.conflicts), ("comment", report.comments)):
        for message in messages:
            print(f"gaps {label}: {message}")
    return None
