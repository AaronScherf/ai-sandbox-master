"""Stage fill: draft the explanation of each proposed node from retrieved passages, in the drafter's own words."""
from __future__ import annotations

from ..ipguard import check_meta, check_prose
from ..store import GraphStore
from ..tasks import Task
from .common import check_citations, neighbour_lines, passage_texts, with_ids

STAGE = "fill"
ALLOWED = {"gist", "explanation", "formal", "example", "citations"}
GIST_MAX = 160

INSTRUCTIONS = """\
Explain this concept for a student studying {subject}, using the offered passages as your source.

Rules:
- Write in your OWN words. Do not copy phrases from the passages: a run of 8 or more consecutive words shared with
  any passage is rejected. (A formal statement in LaTeX may follow the source's notation.)
- Cite only what was offered: each citation is the exact `source` and `ref` shown in an offered passage's header.
- Passages whose source is `lecture` are a student's own notes and may contain mistakes; where they disagree with
  slides, notes, recitation material or a textbook, follow those.
- Say how the concept connects to its neighbours where that helps, but do not invent connections.
- Never mention the passages, the sources, or what they do or do not cover: write as a textbook would, about the
  concept itself. If the passages are thin, write less (and cite what you used); do not comment on it. A result that
  talks about the passages is rejected.
- Finish every sentence and close every $ in your math; write \\$ for a literal dollar sign. A result with an
  odd number of $ is rejected as probably cut off.
- YAML: put `gist` in double quotes; write `explanation`, `formal` and `example` as `|` blocks (use a | block for
  any text with a colon, since an unquoted value containing a colon is invalid YAML); copy each citation's `ref`
  exactly from the passage header and put it in double quotes.

Result: one YAML mapping with these keys:
  gist:         one line, at most 160 characters (the hover label)
  explanation:  a few sentences; LaTeX allowed ($x$ inline)
  formal:       optional formal statement in LaTeX
  example:      optional example or counterexample
  citations:    list of {source: ..., ref: ...} copied from the offered passages
"""


def make_tasks(store: GraphStore, retriever, *, section: str | None = None, nodes: list[str] | None = None,
               redo: bool = False, top_k: int = 6, **_ignored) -> list[Task]:
    graph = store.read_all()
    states = {s.id: (s.state, s.title) for s in graph.sections}
    chosen = []
    for n in graph.nodes:
        state = states.get(n.section, ("planned", n.section))[0]
        if nodes is not None:
            if n.id not in nodes:
                continue
        elif state == "planned" or (section and n.section != section):
            continue
        if n.status == "verified":
            continue
        if n.explanation.strip() and not redo:
            continue
        chosen.append(n)
    hints = store.read_seed_config().fill_hints
    # replace, not format: the instructions contain literal braces ({source: ..., ref: ...})
    instructions = INSTRUCTIONS.replace("{subject}", graph.site.get("subject") or "this course")
    tasks = []
    for n in chosen:
        passages = with_ids(retriever.retrieve(f"{n.name} {n.gist} {n.kind}".strip(), top_k))
        lines = [f"Node: {n.name}   (id: {n.id})", f"Kind: {n.kind}   Topic: {n.topic}",
                 f"Course section: {states.get(n.section, ('', n.section))[1]}",
                 f"Current one-line summary: {n.gist or '(none yet)'}", "Connections already in the graph:"]
        lines += [f"- {s}" for s in neighbour_lines(graph, n.id)] or ["- (none yet)"]
        if hints.get(n.id):
            lines += ["", "The owner asks that this node also covers (state it in the explanation, and put any "
                          "formulas in `formal`):", hints[n.id].strip()]
        tasks.append(Task(id=f"fill-{n.id}", stage=STAGE, subject={"node": n.id}, instructions=instructions,
                          context="\n".join(lines), passages=passages))
    return tasks


def _unclosed_math(text: str) -> bool:
    return text.replace("\\$", "").replace("$$", "").count("$") % 2 == 1


def validate_result(entry: dict, result: dict, store: GraphStore) -> list[str]:
    problems = []
    unknown = sorted(set(result) - ALLOWED)
    if unknown:
        problems.append(f"unknown key(s) {unknown}; allowed: {sorted(ALLOWED)}")
    node_id = entry["subject"]["node"]
    if not any(n.id == node_id for n in store.read_all().nodes):
        problems.append(f"node {node_id!r} no longer exists")
    gist, explanation = result.get("gist"), result.get("explanation")
    if not isinstance(gist, str) or not gist.strip():
        problems.append("gist: required, one line")
    elif "\n" in gist.strip() or len(gist.strip()) > GIST_MAX:
        problems.append(f"gist: must be a single line of at most {GIST_MAX} characters")
    if not isinstance(explanation, str) or not explanation.strip():
        problems.append("explanation: required")
    for key in ("formal", "example"):
        if result.get(key) is not None and not isinstance(result[key], str):
            problems.append(f"{key}: must be text")
    problems += check_citations(result.get("citations"), entry)
    prose = {k: result[k] for k in ("gist", "explanation", "example") if isinstance(result.get(k), str)}
    for name, text in prose.items():
        if _unclosed_math(text):
            problems.append(f"{name}: the math delimiters do not balance (an odd number of $), so a sentence may have "
                            f"been cut off; finish it and close every $ (write \\$ for a literal dollar sign)")
    problems += check_meta(prose)
    problems += check_prose(prose, passage_texts(entry))
    return problems


def apply_result(store: GraphStore, entry: dict, result: dict, provenance: dict) -> str | None:
    node_id = entry["subject"]["node"]
    node = next((n for n in store.read_all().nodes if n.id == node_id), None)
    if node is None:
        return f"node {node_id!r} no longer exists"
    if node.status == "verified":
        return f"node {node_id!r} is verified now; left unchanged"
    changes = {
        "gist": result["gist"].strip(), "explanation": result["explanation"].strip(),
        "citations": [{"source": c["source"], "ref": c["ref"]} for c in result["citations"]],
        "provenance": provenance, "status": "proposed",
    }
    for key in ("formal", "example"):
        if isinstance(result.get(key), str) and result[key].strip():
            changes[key] = result[key].strip()
    store.update_item("node", node_id, changes)
    return None
