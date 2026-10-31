"""What "adjacent context" means: exactly one constraint widened to its sibling terms or its subregion (spec 4.4)."""
from __future__ import annotations

from dataclasses import dataclass

from ..compare import _ancestors
from .corpus import Fact
from .match import Constraint, vocab_for
from .subregions import Subregions


@dataclass(frozen=True)
class Widening:
    constraint: Constraint
    term_ids: frozenset[str] = frozenset()  # sibling terms (intervention, outcome)
    countries: frozenset[str] = frozenset()  # other countries of the subregion
    region: str = ""

    def matches(self, fact: Fact, vocabs: dict) -> bool:
        facet = self.constraint.facet
        if fact.facet != facet:
            return False
        if facet == "countries":
            return fact.shown.upper() in self.countries
        if fact.shown.startswith("proposed:"):
            return False
        return fact.shown in self.term_ids or bool(self.term_ids & _ancestors(fact.shown, vocab_for(facet, vocabs)))

    def label_for(self, fact: Fact, vocabs: dict) -> str:
        facet = self.constraint.facet
        if facet == "countries":
            return f"different country (same subregion: {self.region})"
        vocab = vocab_for(facet, vocabs)
        sibling = fact.shown if fact.shown in self.term_ids else sorted(self.term_ids & _ancestors(fact.shown, vocab))[0]
        n = len(self.term_ids)
        return (f"different {facet} (sibling: {vocab.terms[sibling].label} <- {vocab.terms[self.constraint.value].label}; "
                f"{n} sibling{'' if n == 1 else 's'})")


def widen(c: Constraint, vocabs: dict, subregions: Subregions) -> Widening | None:
    """The widening of one relaxable constraint, or None when it cannot be widened."""
    if c.facet == "countries":
        region = subregions.region_of(c.value)
        others = subregions.members(region) - {c.value.upper()} if region else frozenset()
        return Widening(c, countries=others, region=region) if others else None
    if c.facet not in ("intervention", "outcome"):
        return None
    vocab = vocab_for(c.facet, vocabs)
    if len(c.term_ids) > 1:  # a label group widens to the siblings of every member, never to the members themselves
        parts = [widen(Constraint(c.facet, tid), vocabs, subregions) for tid in c.term_ids]
        siblings = frozenset().union(*(p.term_ids for p in parts if p)) - set(c.term_ids)
        return Widening(c, term_ids=siblings) if siblings else None
    term = vocab.terms.get(c.value) if vocab is not None else None
    # a term whose parent is a top-level grouping would widen to a whole bucket, so it is not widened
    if term is None or term.parent is None or vocab.terms[term.parent].parent is None:
        return None
    siblings = frozenset(t.id for t in vocab.terms.values() if t.parent == term.parent and t.id != term.id)
    return Widening(c, term_ids=siblings) if siblings else None
