"""Build-time validation of a Graph: errors block a build, warnings are reported."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import networkx as nx

from .schema import (
    member_hash,
    CONDITION_REQUIRED, DEFINITIONAL_TYPES, EDGE_TYPES, LOGICAL_TYPES, VIA_ALLOWED, VIA_KINDS,
    Graph, edge_id,
)


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    code: str
    message: str
    ref: str


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == "error"]


def _cycles(edges, types) -> list[list[str]]:
    g = nx.DiGraph()
    for e in edges:
        if e.type in types and e.source != e.target:
            g.add_edge(e.source, e.target)
    return [sorted(c) for c in nx.strongly_connected_components(g) if len(c) > 1]


def validate(graph: Graph) -> list[Issue]:
    issues: list[Issue] = []

    def err(code, message, ref):
        issues.append(Issue("error", code, message, ref))

    def warn(code, message, ref):
        issues.append(Issue("warning", code, message, ref))

    sections = {s.id: s for s in graph.sections}
    nodes = {n.id: n for n in graph.nodes}

    for dup, count in Counter(n.id for n in graph.nodes).items():
        if count > 1:
            err("dup-id", f"node id {dup!r} appears {count} times", dup)
    for dup, count in Counter(e.id for e in graph.edges).items():
        if count > 1:
            err("dup-id", f"edge id {dup!r} appears {count} times", dup)
    for dup, count in Counter(s.id for s in graph.sections).items():
        if count > 1:
            err("dup-id", f"section id {dup!r} appears {count} times", dup)

    for n in graph.nodes:
        if n.section not in sections:
            err("unknown-section", f"node {n.id!r} names unknown section {n.section!r}", n.id)
        if n.kind not in graph.vocab.kinds:
            err("unknown-kind", f"node {n.id!r} has kind {n.kind!r} which is not in config/vocab.yaml", n.id)
        if n.topic not in graph.vocab.topics:
            err("unknown-topic", f"node {n.id!r} has topic {n.topic!r} which is not in config/vocab.yaml", n.id)
        filed_in = graph.node_files.get(n.id)
        if filed_in is not None and filed_in != n.section:
            err("node-file-mismatch", f"node {n.id!r} is in {filed_in}.yaml but its section is {n.section!r}", n.id)

    for e in graph.edges:
        if e.type not in EDGE_TYPES:
            err("unknown-edge-type", f"edge {e.id!r} has unknown type {e.type!r}", e.id)
        if e.id != edge_id(e.source, e.type, e.target):
            err("bad-edge-id", f"edge id {e.id!r} should be {edge_id(e.source, e.type, e.target)!r}", e.id)
        for end in (e.source, e.target):
            if end not in nodes:
                err("dangling-endpoint", f"edge {e.id!r} refers to unknown node {end!r}", e.id)
        if e.source == e.target:
            err("self-loop", f"edge {e.id!r} connects a node to itself", e.id)
        if e.type in CONDITION_REQUIRED and not (e.condition or "").strip():
            err("missing-condition", f"{e.type} edge {e.id!r} needs a condition", e.id)
        if e.via is not None:
            if e.type not in VIA_ALLOWED:
                err("via-not-allowed", f"edge {e.id!r}: 'via' is only allowed on {', '.join(VIA_ALLOWED)}", e.id)
            via_node = nodes.get(e.via)
            if via_node is None or via_node.kind not in VIA_KINDS:
                err("bad-via", f"edge {e.id!r}: via {e.via!r} must be a node of kind {' or '.join(VIA_KINDS)}", e.id)

    for cycle in _cycles(graph.edges, DEFINITIONAL_TYPES):
        err("definitional-cycle", f"definitional edges form a cycle: {', '.join(cycle)}", cycle[0])
    for cycle in _cycles(graph.edges, LOGICAL_TYPES):
        warn("logical-cycle",
             f"these nodes imply each other in a loop; check each edge states its own condition: {', '.join(cycle)}",
             cycle[0])

    linked = {e.source for e in graph.edges} | {e.target for e in graph.edges}
    for n in graph.nodes:
        state = sections[n.section].state if n.section in sections else "planned"
        if state == "planned":
            continue
        if n.id not in linked:
            warn("orphan", f"node {n.id!r} has no edges", n.id)
        if not n.explanation.strip():
            warn("unfilled", f"node {n.id!r} is in a {state} section but has no explanation", n.id)
    members: dict[str, list[str]] = {}
    for n in graph.nodes:
        members.setdefault(n.section, []).append(n.id)
        sec = sections.get(n.section)
        if sec is not None and sec.topic and n.topic != sec.topic:
            err("topic-mismatch", f"node {n.id!r} has topic {n.topic!r} but its section {sec.id!r} has topic "
                                  f"{sec.topic!r}", n.id)
    for sec in graph.sections:
        if sec.state == "planned" or not sec.topic or not members.get(sec.id):
            continue  # summaries are expected once a section declares a topic (a migrated graph)
        if not (sec.summary or "").strip():
            warn("missing-summary", f"section {sec.id!r} has no summary yet", sec.id)
        elif sec.summary_hash != member_hash(members[sec.id]):
            warn("stale-summary", f"section {sec.id!r} changed membership since its summary was drafted", sec.id)
    return issues
