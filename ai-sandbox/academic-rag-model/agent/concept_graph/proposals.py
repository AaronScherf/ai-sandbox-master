"""Reviewer proposals: name similarity, validation and merging. Pure functions; no file access."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import networkx as nx
from pydantic import BaseModel, ConfigDict

from .ipguard import check_meta
from .schema import (CONDITION_REQUIRED, DEFINITIONAL_TYPES, EDGE_TYPES, LOGICAL_TYPES, SLUG, Graph, Node,
                     edge_id)

NAME_MAX = 120
NOTE_MAX = 200
# Words that name a kind of thing rather than a different thing: "Walrasian demand" and "Walrasian demand
# correspondence" are one concept, "Utility function" and "Indirect utility function" are not.
GENERIC = frozenset({"function", "correspondence", "relation", "problem", "theorem", "axiom", "condition",
                     "property", "set", "model", "equation", "lemma", "principle", "assumption"})
_FILLER = frozenset({"of", "the", "a", "an", "and", "for", "in", "to"})


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Connection(_Model):
    other: str
    type: str
    direction: str = "out"          # "out": the new concept is the source; "in": it is the target
    condition: str | None = None
    note: str = ""


class NodeProposal(_Model):
    name: str
    kind: str
    section: str
    topic: str
    note: str = ""
    connections: list[Connection] = []


class EdgeProposal(_Model):
    source: str
    type: str
    target: str
    condition: str | None = None
    note: str = ""


def normalize_name(name: str) -> str:
    text = (name or "").lower().replace("’", "").replace("'", "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def slug_from_name(name: str) -> str:
    return "-".join(normalize_name(name).split())


def _tokens(name: str) -> set[str]:
    return {t for t in normalize_name(name).split() if t not in _FILLER}


def _distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similar_names(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = _tokens(a), _tokens(b)
    if ta and tb:
        small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
        if len(small) >= 2 and small <= big and (big - small) <= GENERIC:
            return True
        if len(ta & tb) / len(ta | tb) >= 0.75:
            return True
    return _distance(na, nb) <= 0.10 * max(len(na), len(nb))


def find_similar_existing(graph: Graph, name: str) -> Node | None:
    return next((n for n in graph.nodes if similar_names(n.name, name)), None)


def check_node(graph: Graph, name: str, kind: str, section: str, topic: str, note: str) -> list[str]:
    problems = []
    if not (name or "").strip():
        problems.append("name is empty")
    elif len(name) > NAME_MAX:
        problems.append(f"name is longer than {NAME_MAX} characters")
    slug = slug_from_name(name)
    if name.strip() and not re.match(SLUG, slug or "!"):
        problems.append(f"name {name!r} does not give a usable id")
    if any(n.id == slug for n in graph.nodes):
        problems.append(f"{slug!r} is already a concept in the graph")
    if any(r.kind == "node" and r.id == slug for r in graph.rejected):
        problems.append(f"{slug!r} was rejected earlier and must not be proposed again")
    if kind not in graph.vocab.kinds:
        problems.append(f"kind {kind!r} is not one of {', '.join(graph.vocab.kinds)}")
    if topic not in graph.vocab.topics:
        problems.append(f"topic {topic!r} is not one of {', '.join(graph.vocab.topics)}")
    if section not in {s.id for s in graph.sections}:
        problems.append(f"section {section!r} does not exist")
    if len(note or "") > NOTE_MAX:
        problems.append(f"note is longer than {NOTE_MAX} characters")
    problems += check_meta({"note": note}) if note else []
    return problems


def check_edge(graph: Graph, source: str, type_: str, target: str, condition: str | None, note: str,
               *, new_ids=frozenset(), staged=()) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one proposed connection. `new_ids` are concepts proposed in the same round;
    `staged` are (source, type, target) triples already accepted earlier in the round."""
    errors: list[str] = []
    warnings: list[str] = []
    known = {n.id for n in graph.nodes} | set(new_ids)
    for label, value in (("source", source), ("target", target)):
        if value not in known:
            errors.append(f"{label} {value!r} is not a concept in the graph")
    if type_ not in EDGE_TYPES:
        errors.append(f"unknown connection type {type_!r}; use one of {', '.join(EDGE_TYPES)}")
    if source == target:
        errors.append("a concept cannot connect to itself")
    if errors:
        return errors, warnings
    eid = edge_id(source, type_, target)
    triples = [(e.source, e.type, e.target) for e in graph.edges] + list(staged)
    have = set(triples)
    if (source, type_, target) in have:
        errors.append(f"{eid} already exists")
    if any(r.kind == "edge" and r.id == eid for r in graph.rejected):
        errors.append(f"{eid} was rejected earlier and must not be proposed again")
    if type_ in CONDITION_REQUIRED and not (condition or "").strip():
        errors.append(f"a {type_} connection needs a condition (when does it hold?)")
    if note:
        errors += check_meta({"note": note})
    if type_ == "implies" and ((source, "iff", target) in have or (target, "iff", source) in have):
        errors.append("redundant: an iff between the same concepts already covers this implies")
    if type_ == "has_property" and (target, "component_of", source) in have:
        errors.append("redundant: the reverse component_of connection already exists")
    if type_ == "component_of" and (target, "has_property", source) in have:
        errors.append("redundant: the reverse has_property connection already exists")
    for group, label, bucket in ((DEFINITIONAL_TYPES, "definitional", errors), (LOGICAL_TYPES, "logical", warnings)):
        if type_ in group:
            g = nx.DiGraph()
            g.add_edges_from((s, d) for s, t, d in triples if t in group and s != d)
            if g.has_node(source) and g.has_node(target) and nx.has_path(g, target, source):
                bucket.append(f"this would close a {label} cycle between {source!r} and {target!r}")
    return errors, warnings
