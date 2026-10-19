"""Stage seed: propose the course outline (sections) and a skeleton of concept nodes from the hub's files.

Seed is for starting a graph (or, with --redo, adding what is missing). It never edits anything that exists; the
owner reviews the skeleton before `fill`. Course-specific knowledge the files cannot carry (what is in scope, which
concepts must appear, which textbook chapters matter) comes from an optional `config/seed.yaml`."""
from __future__ import annotations

import re
from pathlib import Path

from core.course_materials import Catalog, load_catalog

from ..ipguard import check_meta, check_prose
from ..schema import SLUG, SeedConfig
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
_STATEMENT = re.compile(
    r"^[\s*_#>\-]*(definitions?|theorems?|axioms?|lemmas?|propositions?|corollar(?:y|ies)|assumptions?|"
    r"propert(?:y|ies)|postulates?)(\s+\d[\d.]*)?\b[\s:.\-–—]*(.*)$",
    re.IGNORECASE)
_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")
_BORING_HEADINGS = ("related notes", "bibliographic notes", "bibliography", "references", "table of contents", "contents")

KIND_HELP = {
    "object": "a mathematical object or class of objects (a relation, an order, a preference relation)",
    "structure": "a set-up made of several parts (a choice structure, a budget set, a consumer's problem)",
    "property": "a condition an object may satisfy (completeness, transitivity, continuity)",
    "axiom": "an assumed or testable consistency condition on behaviour or preferences (WARP, independence)",
    "definition": "a defined notion that is neither an object nor a property",
    "theorem": "a named result with a proof (an existence, representation or equivalence result)",
    "lemma": "a supporting result used to prove a theorem",
    "model": "a complete economic model or problem (the utility maximization problem, a random utility model)",
    "function": "a function (a utility, expenditure or indirect utility function)",
    "correspondence": "a set-valued map (Walrasian demand)",
    "identity": "an equation that always holds (Roy's identity, Walras' law)",
    "technique": "a method of proof or analysis (a Lagrangian argument, a revealed-preference test)",
    "example": "a named standard example or counterexample",
}

INSTRUCTIONS = """\
Propose the concept-graph skeleton for this course: the course outline (sections) and the concepts (nodes) that
belong in each section. People will review your skeleton before anything is written about each concept.

How to work
1. Read the Subject: the scope, the concepts the owner requires, what is already in the graph, the vocabulary
   (with what each kind means) and the lecture timeline.
2. Read the offered passages. They are extracts of the course's own materials: the syllabus, slide decks (with the
   definitions, axioms and theorems they state), lecture notes, and the contents and section headings of the
   textbook chapters that are in scope. They are your evidence for what the course covers and in what order.
   Weigh them by where they come from: the syllabus, the instructor's slides and notes, recitation material and the
   textbooks are authoritative. Passages whose source is `lecture` are the student's own notes (sometimes expanded by
   a model) and may contain mistakes: use them for teaching order, dates and coverage, and where they disagree with
   class material, follow the class material.
3. Write the result in the format below, then run the self-check.

Sections
- In teaching order. `id` is a slug such as s01-binary-relations; `order` is a unique number (1, 2, 3 ...; fractions
  are fine for inserting later); `title` is short.
- `state`: taught = the course has lecture notes or slides for it; in_progress = only partly covered so far;
  planned = in the syllabus or in the textbook scope but with no lecture material yet.
- `lectures`: the ISO dates from the timeline that belong to the section (leave out if none).
- Follow the order the course teaches (slide-set order and lecture dates) where it differs from the textbooks'. If
  the course relies on background mathematics (sets, relations, orders), give it a first section, however brief.

Concepts
- Include every definition, property, axiom, named theorem or lemma, model, function, correspondence and identity
  that the materials name or use, and that a student must learn. Leave out passing remarks and exercise details.
- One concept per node. A property that other concepts are defined by (for example transitivity) gets its own node.
  An axiom and the theorem relating it to another axiom are separate nodes.
- If the materials use several names for one concept, use the most common as `name` and mention the others in `gist`.
- `kind`: exactly one of the kinds in the Subject, chosen with the explanations given there. `topic`: the thematic
  area; use an existing topic or declare a new slug under `topics`. `gist` (optional): one line, at most 160
  characters, in your own words.

Rules
- ids are slugs (lowercase letters, digits, hyphens), unique across all sections and all nodes, and never reuse an
  id that is already in the graph.
- Do not mention the instructors, teaching assistants or students. Eponymous concept names (Walras' law, Roy's
  identity, the Szpilrajn extension theorem) are fine.
- Do not copy sentences from the materials: 8 or more consecutive words shared with a passage in a `gist` is rejected.
- Every required concept in the Subject must appear as a node, even if the materials barely mention it. The
  required list is a minimum, not the target: expect many more nodes than it contains (typically 6 to 15 per
  section). A section with fewer nodes than the minimum stated in the Subject is rejected, so never leave one empty.
- Never mark anything verified.

Result: one YAML mapping with keys topics (optional), sections and nodes. The example below only shows the format:
its names are placeholders, so do not copy them.

    topics: [example-topic]
    sections:
      - {id: s01-example-section, title: Example section, order: 1, state: taught, lectures: ["2026-09-07"]}
    nodes:
      - {id: example-concept, name: Example concept, kind: property, section: s01-example-section,
         topic: example-topic, gist: "One line saying what it is, in your own words."}

Self-check before you finish (the card is rejected if any of these fail):
  1. Every id is a unique slug, and every node's `section` is one of your sections or an existing one.
  2. Every `kind` is exactly one of the listed kinds; every `topic` is listed or declared under `topics`.
  3. Every required concept appears as a node whose name matches it (or one of its aliases).
  4. No two nodes share a name, and nothing already in the graph is repeated.
  5. Section `order` values are unique numbers and every `state` is taught, in_progress or planned.
  6. Every gist is one line, at most 160 characters, in your own words.
  7. Every section ends up with at least the minimum number of nodes stated in the Subject.
  8. You wrote only inside the yaml fence under "## Result".
"""

ADDITIVE = """\

This graph already has content (listed under Subject). Add ONLY what is missing: new nodes, in existing sections
(use the section's existing id) or in new sections. Do not repeat a concept that is already listed, even under another
name or id. If nothing is missing from a section, leave it alone.
"""


def _title(file_stem: str) -> str:
    text = re.sub(r"^\d+_", "", file_stem).replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def _clean_syllabus(text: str) -> str:
    """The syllabus text minus file metadata and contact details (names, emails, hours, links)."""
    text = _FRONTMATTER.sub("", text.replace("\r\n", "\n"), count=1)
    text = _PAGE_MARK.sub("", text)
    kept = [ln for ln in text.splitlines() if not _PRIVATE_LINE.search(ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def statement_anchors(text: str, limit: int = 25, width: int = 180) -> list[str]:
    """Labelled statements in slides or notes ("Axiom β If x, y ...", "Theorem" followed by its statement), each as
    one line. Slides repeat statements as they build up, so repeats are dropped; a bare label is not an anchor."""
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    out: list[str] = []
    seen: set[str] = set()
    for i, line in enumerate(lines):
        if line.startswith("## Related notes"):
            break
        m = _STATEMENT.match(line)
        if not m:
            continue
        rest = m.group(3).strip(" *_#>:-")
        parts = [rest] if rest else []
        j = i + 1
        while len(" ".join(parts)) < 60 and j < len(lines) and len(parts) < 3:
            nxt = lines[j]
            j += 1
            if not nxt or nxt.startswith("<!--"):
                continue
            if nxt.startswith("#") or _STATEMENT.match(nxt):
                break
            parts.append(nxt)
        if not parts:
            continue
        label = m.group(1).capitalize() + (m.group(2) or "").rstrip(".")
        anchor = re.sub(r"\s+", " ", " ".join([label, *parts])).strip()[:width]
        if anchor.lower() in seen:
            continue
        seen.add(anchor.lower())
        out.append(anchor)
        if len(out) >= limit:
            break
    return out


def section_headings(text: str, limit: int = 40) -> list[str]:
    """Markdown headings of levels 1-3, without boilerplate sections, each once."""
    out: list[str] = []
    for ln in text.replace("\r\n", "\n").split("\n"):
        m = _HEADING.match(ln.strip())
        if not m:
            continue
        title = m.group(2).strip()
        if title.lower().startswith(_BORING_HEADINGS) or title in out:
            continue
        out.append(title)
        if len(out) >= limit:
            break
    return out


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


# Upper bounds on passages per kind of material, so a large role (34 TA notes) cannot crowd out the slides.
ROLE_CAPS = {"instructor": 30, "student_notes": 30, "recitation": 8, "prior": 15}
_CHAPTER_FILE = re.compile(r"/chapters/(\d+)_[^/]*$")


def _evidence(text: str, *, statements: int, headings: int) -> str:
    parts = []
    anchors = statement_anchors(text, limit=statements)
    if anchors:
        parts.append("Statements:\n" + _bullets(anchors))
    heads = section_headings(text, limit=headings) if headings else []
    if heads:
        parts.append("Section headings:\n" + _bullets(heads))
    return "\n\n".join(parts)


def outline_context(hub_root: str, course: str, *, config: SeedConfig | None = None, catalog: Catalog | None = None,
                    max_chars: int = 12000) -> tuple[str, list[Passage]]:
    """Describe the course from its files only (no model, no embedding), by what each file is, class material first.

    Offered passages: the syllabus excerpt (contact details removed); the statements and section headings of the
    instructor's slides and notes; recitation headings; earlier offerings' slide statements; each textbook's contents
    and the headings of the chapters the config puts in scope; and last, the statements and headings of the student's
    lecture notes. The context text carries the lecture dates and teaching order and points to the passages."""
    config = config or SeedConfig()
    catalog = catalog if catalog is not None else load_catalog(hub_root, course)
    hub = Path(hub_root)
    lines: list[str] = []
    passages: list[Passage] = []

    def read(m) -> str:
        return (hub / m.path).read_text(encoding="utf-8", errors="ignore")

    def add(m, text: str, ref: str | None = None) -> None:
        source, default_ref = classify_passage(m.path, "", catalog)
        passages.append(Passage(id="", source=source, ref=ref or default_ref, text=text, path=str(hub / m.path)))

    seen_text: set[str] = set()
    for m in catalog.by_role("syllabus"):
        text = _clean_syllabus(read(m))[:3000].strip()
        if text and text not in seen_text:
            seen_text.add(text)
            add(m, text)

    titles: list[str] = []
    lecture_dates: set[str] = set()
    for m in catalog.by_role("instructor")[: ROLE_CAPS["instructor"]]:
        label = classify_passage(m.path, "", catalog)[1]
        evidence = _evidence(read(m), statements=25, headings=20)
        handwritten = m.format == "handwritten"
        if evidence:
            what = f"the instructor's notes of {label}" if handwritten else "these slides"
            add(m, f"Found in {what}:\n\n{evidence}")
        if handwritten and m.date:
            lecture_dates.add(m.date)
        if label not in titles:
            titles.append(label)

    for m in catalog.by_role("recitation")[: ROLE_CAPS["recitation"]]:
        heads = section_headings(read(m), limit=15)
        if heads:
            add(m, "Section headings:\n" + _bullets(heads))

    prior_lines: list[str] = []
    for label in catalog.offerings():
        decks: list[str] = []
        for m in [x for x in catalog.by_role("instructor", offering=label) if x.format == "slides"][: ROLE_CAPS["prior"]]:
            title = classify_passage(m.path, "", catalog)[1]
            anchors = statement_anchors(read(m))
            if anchors:
                add(m, f"Statements found in the {label} offering slides:\n" + _bullets(anchors))
            if title not in decks:
                decks.append(title)
        if decks:
            prior_lines += [f"{label} offering slide sets (in order): " + "; ".join(decks), ""]

    by_name = {k.lower(): v for k, v in config.textbook_chapters.items()}
    books: dict[str, list] = {}
    for m in catalog.by_role("textbook"):
        books.setdefault(m.book or "book", []).append(m)
    for key in sorted(books):
        chapters = sorted(((int(c.group(1)), m) for m in books[key] if (c := _CHAPTER_FILE.search(m.path))
                           and int(c.group(1)) > 0), key=lambda pair: (pair[0], pair[1].path))
        if not chapters:
            continue
        folder = chapters[0][1].path.split("/")[-3].lower()
        wanted = set(config.textbook_chapters.get(key) or by_name.get(key.lower()) or by_name.get(folder) or [])
        toc = []
        for number, m in chapters:
            toc.append(f"{number}. {_title(m.stem)}")
            if number in wanted:
                heads = section_headings(read(m))
                if heads:
                    add(m, f"Section headings of chapter {number} ({_title(m.stem)}):\n" + _bullets(heads),
                        ref=f"ch. {number} section headings")
        add(chapters[0][1], "\n".join(toc), ref="table of contents")

    # The student's own notes come last: they fix teaching order and dates, but class material outranks them.
    by_date: dict[str, list] = {}
    for m in catalog.by_role("student_notes"):
        if m.date:
            by_date.setdefault(m.date, []).append(m)
    for date in sorted(by_date)[: ROLE_CAPS["student_notes"]]:
        evidence = "\n\n".join(e for e in (_evidence(read(m), statements=12, headings=12) for m in by_date[date]) if e)
        if evidence:
            add(by_date[date][0], f"Found in the student's lecture notes of {date}:\n\n{evidence}", ref=date)
    lecture_dates |= set(by_date)

    if lecture_dates:
        lines += ["Lecture dates with notes: " + ", ".join(sorted(lecture_dates)), ""]
    if titles:
        lines += ["Instructor slides and notes (in course order): " + "; ".join(titles), ""]
    lines += prior_lines
    lines += ["The syllabus excerpt, what was found in the instructor's slides and notes and in the lecture notes, and "
              "the textbook contents and section headings are under 'Offered passages' below."]
    context = "\n".join(lines).strip()
    if len(context) > max_chars:
        context = context[:max_chars] + "\n[context truncated]"
    return context, passages


def _norm(name: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", name.lower().replace("'", "").replace("’", "")).split())


def _aliases(entry) -> list[str]:
    return [entry] if isinstance(entry, str) else list(entry)


def _matches(alias: str, name: str) -> bool:
    a, n = _norm(alias), _norm(name)
    return bool(a) and (a == n or f" {a} " in f" {n} ")


def make_tasks(store: GraphStore, retriever=None, *, hub_root: str | None = None, course: str | None = None,
               redo: bool = False, catalog: Catalog | None = None, **_ignored) -> list[Task]:
    if not hub_root or not course:
        raise ValueError("seed needs --hub-root and --course")
    graph = store.read_all()
    has_content = bool(graph.sections or graph.nodes)
    if any(s.state in ("taught", "in_progress") for s in graph.sections) and not redo:
        raise ValueError("the graph already has taught sections; seed is for starting a graph (use --redo to add to it)")
    config = store.read_seed_config()
    context, passages = outline_context(hub_root, course, config=config, catalog=catalog)

    existing =[f"- section {s.id} (order {s.order:g}, {s.state}): {s.title}" for s in graph.sections]
    existing += [f"- node {n.id}: {n.name} (section {n.section})" for n in graph.nodes]
    required = []
    for entry in config.must_include:
        names = _aliases(entry)
        required.append(names[0] + (f"   (also written: {'; '.join(names[1:])})" if len(names) > 1 else ""))
    kinds = [f"- {k}: {KIND_HELP.get(k, '(no description)')}" for k in graph.vocab.kinds]
    body = "\n".join([
        f"Course: {course}", "",
        "Scope (from the owner):", config.scope.strip() or "(none given: use the syllabus)", "",
        "Required concepts (each must appear as a node; this list is only a floor):", *(required or ["(none specified)"]), "",
        f"Every section must end up with at least {config.min_nodes_per_section} nodes (existing nodes count).", "",
        "Kinds (use exactly these words):", *kinds, "",
        "Topics so far: " + ", ".join(graph.vocab.topics), "",
        "Already in the graph (do not reuse these ids or repeat these concepts):", *(existing or ["- (nothing yet)"]), "",
        "Course materials:", context or "(no materials found)",
    ])
    instructions = INSTRUCTIONS + (ADDITIVE if has_content else "")
    return [Task(id="seed", stage=STAGE,
                 subject={"stage": "seed", "must_include": config.must_include,
                          "min_nodes_per_section": config.min_nodes_per_section},
                 instructions=instructions, context=body, passages=with_ids(passages))]


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
    names_seen = {_norm(n.name): n for n in graph.nodes}
    new_names: dict[str, str] = {}
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
        name = n.get("name")
        if not isinstance(name, str) or not name.strip():
            problems.append(f"{tag}: name is required")
        else:
            key = _norm(name)
            if key in names_seen:
                other = names_seen[key]
                problems.append(f"{tag}: name {name!r} already exists as node {other.id!r} ({other.name})")
            elif key in new_names:
                problems.append(f"{tag}: name {name!r} duplicates node {new_names[key]!r} in this result")
            else:
                new_names[key] = nid if isinstance(nid, str) else "?"
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
                problems += [f"{tag} {m}" for m in check_meta({"gist": gist})]
                problems += [f"{tag} {m}" for m in check_prose({"gist": gist}, passage_texts(entry))]

    floor = (entry.get("subject", {}) or {}).get("min_nodes_per_section", 1)
    counts = {sid: 0 for sid in section_ids}
    for n in graph.nodes:
        counts[n.section] = counts.get(n.section, 0) + 1
    for n in nodes:
        if isinstance(n, dict) and n.get("section") in counts:
            counts[n["section"]] += 1
    for sid in sorted(counts):
        if counts[sid] < floor:
            problems.append(f"section {sid!r} would end up with only {counts[sid]} node(s); each section needs at least "
                            f"{floor} (add the concepts a student must learn in it)")

    all_names = [n.name for n in graph.nodes] + [n["name"] for n in nodes if isinstance(n, dict) and isinstance(n.get("name"), str)]
    missing = []
    for required in (entry.get("subject", {}).get("must_include") or []):
        aliases = _aliases(required)
        if not any(_matches(a, name) for a in aliases for name in all_names):
            missing.append(aliases[0] + (f" (or {', '.join(aliases[1:])})" if len(aliases) > 1 else ""))
    if missing:
        problems.append("required concept(s) missing: " + "; ".join(missing)
                        + ". Add each as a node (any reasonable id); its name must match.")
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
