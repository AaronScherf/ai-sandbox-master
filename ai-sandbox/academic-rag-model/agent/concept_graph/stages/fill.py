"""Stage fill: draft the explanation of each proposed node from retrieved passages, in the drafter's own words."""
from __future__ import annotations

from ..ipguard import check_prose
from ..store import GraphStore
from ..tasks import Task
from .common import check_citations, neighbour_lines, passage_texts, with_ids

STAGE = "fill"
ALLOWED = {"gist", "explanation", "formal", "example", "citations"}
GIST_MAX = 160

INSTRUCTIONS = """\
Explain this concept for a graduate student studying microeconomic theory, using the offered passages as your source.

Rules:
- Write in your OWN words. Do not copy phrases from the passages: a run of 8 or more consecutive words shared with
  any passage is rejected. (A formal statement in LaTeX may follow the source's notation.)
- Cite only what was offered: each citation is the exact `source` and `ref` shown in an offered passage's header.
- Say how the concept connects to its neighbours where that helps, but do not invent connections.
- If the passages do not support the concept, say so in `explanation` and cite what you did use.

Result: one YAML mapping with these keys:
  gist:         one line, at most 160 characters (the hover label)
  explanation:  a few sentences; LaTeX allowed ($x$ inline)
  formal:       optional formal statement in LaTeX
  example:      optional example or counterexample
  citations:    list of {source: ..., ref: ...} copied from the offered passages
"""


def make_tasks(store: GraphStore, retriever, *, section: str | None = None, nodes: list[str] | None = None,
               redo: bool = False, top_k: int = 6) -> list[Task]:
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
    tasks = []
    for n in chosen:
        passages = with_ids(retriever.retrieve(f"{n.name} {n.gist} {n.kind}".strip(), top_k))
        lines = [f"Node: {n.name}   (id: {n.id})", f"Kind: {n.kind}   Topic: {n.topic}",
                 f"Course section: {states.get(n.section, ('', n.section))[1]}",
                 f"Current one-line summary: {n.gist or '(none yet)'}", "Connections already in the graph:"]
        lines += [f"- {s}" for s in neighbour_lines(graph, n.id)] or ["- (none yet)"]
        tasks.append(Task(id=f"fill-{n.id}", stage=STAGE, subject={"node": n.id}, instructions=INSTRUCTIONS,
                          context="\n".join(lines), passages=passages))
    return tasks


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
