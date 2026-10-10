"""Helpers shared by the drafting stages."""
from __future__ import annotations

import dataclasses

from ..schema import Graph
from ..sources import Passage

_SENTENCES = {
    "is_a": lambda s, t, c: f"{s} is a {t}" + (f", that also: {c}" if c else ""),
    "has_property": lambda s, t, c: f"{s} has the property {t}",
    "defined_on": lambda s, t, c: f"{s} is defined on {t}",
    "component_of": lambda s, t, c: f"{s} is one of the conditions making up {t}",
    "implies": lambda s, t, c: f"{s} implies {t}" + (f", when: {c}" if c else ""),
    "iff": lambda s, t, c: f"{s} holds exactly when {t}" + (f", given: {c}" if c else ""),
    "hypothesis_of": lambda s, t, c: f"{s} is a hypothesis of {t}",
    "yields": lambda s, t, c: f"{s} yields {t}",
    "counterexample_to": lambda s, t, c: f"{s} is a counterexample showing the converse of {t} fails",
}


def edge_sentence(edge, names: dict[str, str]) -> str:
    """The same wording the viewer uses, so cards and the page read alike."""
    make = _SENTENCES.get(edge.type)
    s, t = names.get(edge.source, edge.source), names.get(edge.target, edge.target)
    text = make(s, t, edge.condition) if make else f"{s} - {edge.type} - {t}"
    if edge.via:
        text += f" (via {names.get(edge.via, edge.via)})"
    return text


def neighbour_lines(graph: Graph, node_id: str) -> list[str]:
    names = {n.id: n.name for n in graph.nodes}
    return [edge_sentence(e, names) for e in graph.edges if node_id in (e.source, e.target, e.via)]


def with_ids(passages: list[Passage]) -> list[Passage]:
    return [dataclasses.replace(p, id=f"P{i}") for i, p in enumerate(passages, 1)]


def passage_texts(entry: dict) -> list[str]:
    return [p["text"] for p in entry.get("passages", [])]


def check_citations(citations, entry: dict) -> list[str]:
    """Every citation must be a (source, ref) pair that was offered on this task's card."""
    if not isinstance(citations, list) or not citations:
        return ["citations: give at least one, copied exactly (source and ref) from an offered passage"]
    offered = {tuple(o) for o in entry.get("offered", [])}
    problems = []
    for c in citations:
        if not isinstance(c, dict) or set(c) != {"source", "ref"}:
            problems.append(f"citations: each entry must be exactly {{source, ref}}, got {c!r}")
        elif (c["source"], c["ref"]) not in offered:
            problems.append(f"citations: {c['source']} / {c['ref']} was not offered on this card; cite only offered passages")
    return problems


def provenance(driver: str, agent: str | None, run: str) -> dict:
    return {"driver": driver, "agent": agent, "run": run}
