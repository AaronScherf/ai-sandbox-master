"""Stage link: propose typed, conditioned edges between existing nodes, grounded in retrieved passages."""
from __future__ import annotations

from pydantic import ValidationError

from ..ipguard import check_meta, check_prose
from ..schema import (
    CONDITION_REQUIRED, EDGE_TYPES, VIA_ALLOWED, VIA_KINDS, Citation, Edge, edge_id,
)
from ..store import GraphStore
from ..tasks import Task
from ..validate import errors, validate
from .common import check_citations, edge_sentence, passage_texts, with_ids

STAGE = "link"
EDGE_KEYS = {"source", "type", "target", "condition", "via", "explanation", "citations"}

INSTRUCTIONS = """\
Propose how this concept connects to the OTHER concepts listed under Subject, using the offered passages as evidence.

Edge types (source -> target):
  is_a              source is a kind of target; `condition` says what it adds
  has_property      source has the property target
  defined_on        source is defined on target (a set or a relation)
  component_of      source is one of the conditions making up the bundle target
  implies / iff     source implies (or is equivalent to) target; `condition` is REQUIRED: the assumptions needed
  hypothesis_of     source is an input to the theorem target
  yields            the theorem source yields target
  counterexample_to source shows the converse of target fails
  uses              source uses target as an essential input to a calculation, test or derivation
  applies_to        source can be applied to target; this is a nonexclusive application, not a prerequisite
  estimates         source is a sample-based rule estimating the population target
  computed_from     source is calculated from target by a stated formula
  variant_of        source modifies target's method or objective but is not a taxonomic subtype
`via` (only on implies/iff) names the theorem node that justifies the edge.

Rules:
- Use only node ids from the candidate list. One end of every edge must be this task's node.
- Do not repeat an existing edge and do not propose a rejected one (both are listed).
- Write `explanation` (and `condition`) in your OWN words; 8 or more consecutive words shared with a passage is rejected.
- Cite only offered passages: copy `source` and `ref` exactly.
- Explain the relationship itself; never mention the passages or sources in `explanation` or `condition`.
- State any condition needed for the relationship to hold; it is shown in the graph sentence.
- It is fine to propose no edges: return `edges: []`. A wrong implication is worse than a missing one.

Result: one YAML mapping:
  edges:
    - source: <node id>
      type: <one of the types>
      target: <node id>
      condition: <text, required for implies/iff>
      via: <theorem node id, optional>
      explanation: <why, in your own words>
      citations: [{source: ..., ref: ...}]
"""


def make_tasks(store: GraphStore, retriever, *, section: str | None = None, nodes: list[str] | None = None,
               redo: bool = False, top_k: int = 6, **_ignored) -> list[Task]:
    graph = store.read_all()
    states = {s.id: (s.state, s.title) for s in graph.sections}
    names = {n.id: n.name for n in graph.nodes}
    touched = {end for e in graph.edges for end in (e.source, e.target)}
    tasks = []
    for n in graph.nodes:
        state = states.get(n.section, ("planned", n.section))[0]
        if nodes is not None:
            if n.id not in nodes:
                continue
        elif state == "planned" or (section and n.section != section):
            continue
        if not n.explanation.strip():
            continue
        if n.id in touched and not redo:
            continue
        passages = with_ids(retriever.retrieve(f"{n.name} {n.gist} implies equivalent necessary sufficient", top_k))
        lines = [f"This task's node: {n.name}   (id: {n.id}, kind: {n.kind})", f"Its summary: {n.gist or '(none)'}", "",
                 "Candidate nodes (id | name | kind | course section | summary):"]
        for other in graph.nodes:
            if other.id != n.id:
                lines.append(f"- {other.id} | {other.name} | {other.kind} | {states.get(other.section, ('', other.section))[1]}"
                             f" | {other.gist or '(no summary yet)'}")
        mine = [e for e in graph.edges if n.id in (e.source, e.target, e.via)]
        lines += ["", "Edges that already exist for this node (do not repeat):"]
        lines += [f"- {edge_sentence(e, names)}   [{e.id}]" for e in mine] or ["- (none)"]
        gone = [r.id for r in graph.rejected if r.kind == "edge" and n.id in r.id.split("--")]
        if gone:
            lines += ["", "Rejected edges (never propose these again):"] + [f"- {g}" for g in gone]
        tasks.append(Task(id=f"link-{n.id}", stage=STAGE, subject={"node": n.id}, instructions=INSTRUCTIONS,
                          context="\n".join(lines), passages=passages))
    return tasks


def validate_result(entry: dict, result: dict, store: GraphStore) -> list[str]:
    problems = []
    unknown = sorted(set(result) - {"edges"})
    if unknown:
        problems.append(f"unknown key(s) {unknown}; the result has only an `edges` list")
    edges = result.get("edges")
    if not isinstance(edges, list):
        return problems + ["edges: must be a list (use `edges: []` for none)"]
    graph = store.read_all()
    node_id = entry["subject"]["node"]
    kinds = {n.id: n.kind for n in graph.nodes}
    if node_id not in kinds:
        return problems + [f"node {node_id!r} no longer exists"]
    existing = {e.id for e in graph.edges}
    tombstones = {r.id for r in graph.rejected if r.kind == "edge"}
    seen: set[str] = set()
    new_edges: list[Edge] = []
    for i, e in enumerate(edges, 1):
        tag = f"edge {i}"
        if not isinstance(e, dict):
            problems.append(f"{tag}: must be a mapping")
            continue
        extra = sorted(set(e) - EDGE_KEYS)
        if extra:
            problems.append(f"{tag}: unknown key(s) {extra}; allowed: {sorted(EDGE_KEYS)} (ids are computed for you)")
        src, typ, tgt = e.get("source"), e.get("type"), e.get("target")
        ok = True
        for label, value in (("source", src), ("target", tgt)):
            if value not in kinds:
                problems.append(f"{tag}: {label} {value!r} is not a node id in the candidate list")
                ok = False
        if typ not in EDGE_TYPES:
            problems.append(f"{tag}: unknown edge type {typ!r}; use one of {', '.join(EDGE_TYPES)}")
            ok = False
        if not ok:
            continue
        if src == tgt:
            problems.append(f"{tag}: connects {src!r} to itself")
            continue
        if node_id not in (src, tgt):
            problems.append(f"{tag}: one end must be this task's node {node_id!r}")
        eid = edge_id(src, typ, tgt)
        if eid in existing:
            continue  # two cards often propose the same edge from opposite ends; the graph already has it
        if eid in tombstones:
            problems.append(f"{tag}: {eid} was rejected earlier and must not be proposed again")
        if eid in seen:
            problems.append(f"{tag}: {eid} appears twice in this result")
        seen.add(eid)
        condition = e.get("condition")
        if typ in CONDITION_REQUIRED and not (isinstance(condition, str) and condition.strip()):
            problems.append(f"{tag}: {typ} needs a `condition`")
        via = e.get("via")
        if via is not None:
            if typ not in VIA_ALLOWED:
                problems.append(f"{tag}: `via` is only allowed on {' and '.join(VIA_ALLOWED)} edges")
            elif kinds.get(via) not in VIA_KINDS:
                problems.append(f"{tag}: via {via!r} must be a theorem or lemma node")
        explanation = e.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            problems.append(f"{tag}: explanation is required")
        prose = {f"{tag} explanation": explanation if isinstance(explanation, str) else "",
                 f"{tag} condition": condition if isinstance(condition, str) else ""}
        problems += check_meta(prose)
        problems += check_prose(prose, passage_texts(entry))
        problems += [f"{tag}: {m}" for m in check_citations(e.get("citations"), entry)]
        try:
            new_edges.append(Edge(
                id=eid, source=src, type=typ, target=tgt,
                condition=condition if isinstance(condition, str) else None,
                via=via if isinstance(via, str) else None,
                explanation=explanation if isinstance(explanation, str) else "",
                citations=[Citation(**c) for c in e.get("citations", []) if isinstance(c, dict) and set(c) == {"source", "ref"}]))
        except ValidationError:
            problems.append(f"{tag}: could not be read as an edge")
    if new_edges and not problems:
        before = {(i.code, i.ref) for i in errors(validate(graph))}
        graph.edges.extend(new_edges)
        for issue in errors(validate(graph)):
            if issue.code == "definitional-cycle" and (issue.code, issue.ref) not in before:
                problems.append(f"these edges would create a definitional cycle: {issue.message}")
    return problems


def apply_result(store: GraphStore, entry: dict, result: dict, provenance: dict) -> str | None:
    edges = result.get("edges") or []
    if not edges:
        return None
    existing = {e.id for e in store.read_all().edges}
    prepared = []
    for e in edges:
        eid = edge_id(e["source"], e["type"], e["target"])
        if eid in existing:
            continue
        item = {"id": eid, "source": e["source"], "type": e["type"], "target": e["target"],
                "condition": e.get("condition"), "via": e.get("via"), "explanation": e["explanation"].strip(),
                "citations": [{"source": c["source"], "ref": c["ref"]} for c in e["citations"]],
                "status": "proposed", "provenance": provenance}
        prepared.append(item)
    if not prepared:
        return None
    try:
        store.add_edges(prepared)
    except ValueError as exc:
        return f"{exc}; nothing applied"
    return None
