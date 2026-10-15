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
# A word like these in only one of two names makes them different concepts, however close the spelling.
QUALIFIERS = frozenset({"strictly", "strict", "locally", "globally", "weak", "weakly", "strong", "strongly", "non",
                        "not", "anti", "quasi", "marginal", "relative", "absolute", "average"})
_NEGATING_PREFIXES = ("un", "non", "in", "im", "ir", "dis")


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
    topic: str = ""  # ignored when the section declares a topic
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


def _opposed(ta: set[str], tb: set[str]) -> bool:
    """True when the names differ by a qualifier or by a negating prefix ("compensated" and "uncompensated")."""
    only_a, only_b = ta - tb, tb - ta
    if (only_a | only_b) & QUALIFIERS:
        return True
    for x in only_a:
        for y in only_b:
            if any(y == pre + x or x == pre + y for pre in _NEGATING_PREFIXES):
                return True
    return False


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
        if _opposed(ta, tb):
            return False
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
    sec = next((s for s in graph.sections if s.id == section), None)
    if not (sec and sec.topic) and topic not in graph.vocab.topics:
        problems.append(f"topic {topic!r} is not one of {', '.join(graph.vocab.topics)}")
    if sec is None:
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
    if len(note or "") > NOTE_MAX:
        errors.append(f"note is longer than {NOTE_MAX} characters")
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




@dataclass
class Merged:
    name: str
    kind: str
    section: str
    topic: str
    note: str
    connections: list[Connection]
    reviewers: list[str]
    decisions: list[str] = field(default_factory=list)


def cluster(items: list[tuple[NodeProposal, str]]) -> list[list[tuple[NodeProposal, str]]]:
    """Group proposals whose names are similar (transitively), keeping first-seen order of groups."""
    groups: list[list[tuple[NodeProposal, str]]] = []
    for item in items:
        hits = [g for g in groups if any(similar_names(item[0].name, other[0].name) for other in g)]
        if not hits:
            groups.append([item])
            continue
        hits[0].append(item)
        for extra in hits[1:]:
            hits[0].extend(extra)
            groups.remove(extra)
    return groups


def _majority(values: list[tuple[str, str]], label: str) -> tuple[str, list[str]]:
    """values are (value, reviewer). A tie is broken by reviewer name, never by read order, and reported."""
    counts = Counter(v for v, _ in values)
    top = max(counts.values())
    leaders = sorted((v for v, c in counts.items() if c == top))
    if len(leaders) == 1:
        return leaders[0], []
    first = min((r, v) for v, r in values if v in leaders)
    detail = "; ".join(f"{r} chose {v}" for v, r in sorted(values, key=lambda x: (x[1], x[0])))
    return first[1], [f"{label} needs a decision: {detail} (written as {first[1]!r} by name order)"]


def merge_cluster(items: list[tuple[NodeProposal, str]]) -> Merged:
    decisions: list[str] = []
    forms = Counter(normalize_name(p.name) for p, _ in items)
    top = max(forms.values())
    best = sorted((f for f, c in forms.items() if c == top), key=lambda f: (-len(f), f))[0]
    name = next(p.name for p, _ in items if normalize_name(p.name) == best)
    chosen = {}
    for label in ("kind", "section"):
        chosen[label], flagged = _majority([(getattr(p, label), who) for p, who in items], label)
        decisions += flagged
    topics = [(p.topic, who) for p, who in items if p.topic]
    chosen["topic"], flagged = _majority(topics, "topic") if topics else ("", [])
    decisions += flagged
    conns: dict[tuple[str, str, str], Connection] = {}
    for p, who in items:
        for c in p.connections:
            key = (c.other, c.type, c.direction)
            if key not in conns:
                conns[key] = c.model_copy()
            else:
                have = conns[key]
                parts = sorted({x for x in (have.condition, c.condition) if x})
                have.condition = "; ".join(parts) or None
    reviewers = sorted({who for _, who in items})
    notes = [(who, p.note.strip()) for p, who in sorted(items, key=lambda i: i[1]) if p.note.strip()]
    if len(items) == 1:
        note = notes[0][1] if notes else ""
    else:
        note = " | ".join(f"{who}: {text}" for who, text in notes)
    if len(note) > NOTE_MAX:
        note = note[: NOTE_MAX - 1].rstrip() + "…"
    return Merged(name=name, note=note, connections=list(conns.values()), reviewers=reviewers,
                  decisions=decisions, **chosen)


def merge_edges(items: list[tuple[EdgeProposal, str]]) -> list[tuple[EdgeProposal, list[str]]]:
    """Collapse proposals for the same edge id; conditions and notes are joined, reviewers kept."""
    out: dict[str, tuple[EdgeProposal, list[str], list[tuple[str, str]]]] = {}
    for e, who in items:
        key = edge_id(e.source, e.type, e.target)
        if key not in out:
            out[key] = (e.model_copy(), [who], [(who, e.note.strip())] if e.note.strip() else [])
            continue
        have, who_list, notes = out[key]
        parts = sorted({x for x in (have.condition, e.condition) if x})
        have.condition = "; ".join(parts) or None
        if who not in who_list:
            who_list.append(who)
        if e.note.strip():
            notes.append((who, e.note.strip()))
    result = []
    for have, who_list, notes in out.values():
        if len(notes) > 1:
            have.note = " | ".join(f"{w}: {t}" for w, t in sorted(notes))[:NOTE_MAX]
        elif notes:
            have.note = notes[0][1] if len(who_list) == 1 else f"{notes[0][0]}: {notes[0][1]}"
        result.append((have, sorted(who_list)))
    return result
