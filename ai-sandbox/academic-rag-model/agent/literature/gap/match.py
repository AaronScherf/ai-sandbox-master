"""Matching a resolved constraint against a paper's tier A/B facts, by term id (descendants included)."""
from __future__ import annotations

from dataclasses import dataclass

from .. import schema
from ..compare import _ancestors
from ..transcript import normalize
from .corpus import Corpus, Fact


@dataclass(frozen=True)
class Constraint:
    facet: str
    value: str  # a resolved term id, or an upper-case ISO alpha-2 code for `countries`
    phrase: str = ""
    resolved_by: str = "exact"


def vocab_for(facet: str, vocabs: dict):
    name = schema.FACETS.get(facet)
    return vocabs.get(name) if name else None


def fact_matches(c: Constraint, fact: Fact, vocabs: dict) -> bool:
    if c.facet == "countries":
        return fact.facet == "countries" and fact.shown.upper() == c.value.upper()
    if fact.facet != c.facet:
        return False
    vocab = vocab_for(c.facet, vocabs)
    if fact.shown.startswith("proposed:"):
        term = vocab.terms.get(c.value) if vocab is not None else None
        return term is not None and normalize(fact.label) == normalize(term.label)
    return fact.shown == c.value or c.value in _ancestors(fact.shown, vocab)


def papers_matching(corpus: Corpus, constraints: list[Constraint], vocabs: dict) -> list[str]:
    """File ids where every constraint matches some fact."""
    return sorted(fid for fid, facts in corpus.facts.items()
                  if all(any(fact_matches(c, f, vocabs) for f in facts) for c in constraints))
