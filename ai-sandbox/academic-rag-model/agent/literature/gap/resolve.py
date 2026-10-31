"""Turn a phrase into one resolved constraint, or stop with ranked candidates for the user (or the card) to pick from."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..cluster import FACETS
from ..compare import _ancestors
from ..vocab import _key, is_country
from .corpus import Corpus
from .match import Constraint, papers_matching, vocab_for
from .subregions import Subregions, load_subregions

_STOP = {"a", "an", "and", "the", "of", "in", "on", "for", "to", "with", "by"}
_DEFINITION_WEIGHT = 0.25


@dataclass(frozen=True)
class Candidate:
    term_id: str
    label: str
    level: int
    children: int
    papers: int
    path: str = ""  # ancestor labels, root first: tells same-label terms in different branches apart


@dataclass
class Resolution:
    constraint: Constraint | None = None
    candidates: list[Candidate] = field(default_factory=list)
    message: str = ""


def level_of(term_id: str, vocab) -> int:
    return len(_ancestors(term_id, vocab))


def _tokens(text) -> set[str]:
    words = re.findall(r"[a-z0-9]+", _key(text))
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words if w not in _STOP}


def _path(term_id: str, vocab) -> str:
    labels, parent = [], vocab.terms[term_id].parent
    while parent in vocab.terms and len(labels) < 20:
        labels.append(vocab.terms[parent].label)
        parent = vocab.terms[parent].parent
    return " > ".join(reversed(labels))


def full_path(term_id: str, vocab) -> str:
    """Ancestor labels and the term's own label, root first; the label alone for a root term."""
    above = _path(term_id, vocab)
    return f"{above} > {vocab.terms[term_id].label}" if above else vocab.terms[term_id].label


def _candidate(corpus: Corpus, vocabs: dict, facet: str, vocab, term_id: str) -> Candidate:
    term = vocab.terms[term_id]
    return Candidate(term_id, term.label, level_of(term_id, vocab),
                     sum(1 for t in vocab.terms.values() if t.parent == term_id),
                     len(papers_matching(corpus, [Constraint(facet, term_id)], vocabs)), _path(term_id, vocab))


GROUP_PREFIX = "group:"


def label_group(vocab, term_id: str) -> list[str]:
    """Every term id (sorted) that shares `term_id`'s label, case- and space-insensitively."""
    key = _key(vocab.terms[term_id].label)
    return sorted(t.id for t in vocab.terms.values() if _key(t.label) == key)


def shortlist(corpus: Corpus, vocabs: dict, facet: str, text: str, limit: int = 8) -> list[Candidate]:
    """Terms ranked by token overlap of `text` with label and aliases (definition at lower weight); no model."""
    vocab = vocab_for(facet, vocabs)
    if vocab is None:
        return []
    query = _tokens(text)
    if not query:
        return []
    scored = []
    for term in vocab.terms.values():
        name = max((len(query & t) / len(query | t) for t in map(_tokens, (term.label, *term.aliases)) if t), default=0.0)
        definition = len(query & _tokens(term.definition)) / len(query) * _DEFINITION_WEIGHT if term.definition else 0.0
        if name + definition > 0:
            scored.append((-(name + definition), term.id))
    return [_candidate(corpus, vocabs, facet, vocab, tid) for _, tid in sorted(scored)[:limit]]


def _resolve_country(corpus, vocabs, value, pick, resolved_by, subregions, limit) -> Resolution:
    subregions = subregions or load_subregions()
    if pick is not None:
        if is_country(pick.upper()):
            return Resolution(Constraint("countries", pick.upper(), value, resolved_by))
        return Resolution(message=f"{pick!r} is not an ISO 3166-1 alpha-2 country code")
    code = value.strip().upper()
    if is_country(code):
        return Resolution(Constraint("countries", code, value, "exact"))
    codes = subregions.codes_for_name(value)
    if len(codes) == 1:
        return Resolution(Constraint("countries", codes[0], value, "exact"))
    if not codes:
        return Resolution(message=f"no country matches {value!r}; use an ISO 3166-1 alpha-2 code")
    cands = [Candidate(c, subregions.names.get(c, c), 0, 0,
                       len(papers_matching(corpus, [Constraint("countries", c)], vocabs))) for c in codes[:limit]]
    return Resolution(candidates=cands, message=f"{value!r} matches several countries; pick a code")


def resolve(corpus: Corpus, vocabs: dict, facet: str, value: str, *, pick: str | None = None,
            resolved_by: str = "user", subregions: Subregions | None = None, limit: int = 8) -> Resolution:
    if facet not in FACETS:
        raise ValueError(f"{facet!r}: use a facet from {', '.join(FACETS)}")
    if facet == "countries":
        return _resolve_country(corpus, vocabs, value, pick, resolved_by, subregions, limit)
    vocab = vocab_for(facet, vocabs)
    if vocab is None:
        raise ValueError(f"no vocabulary is loaded for facet {facet!r}")
    if pick is not None:
        if pick.startswith(GROUP_PREFIX):
            base = pick[len(GROUP_PREFIX):]
            members = label_group(vocab, base) if base in vocab.terms else []
            if len(members) < 2:
                return Resolution(message=f"{pick!r}: no other term of the {vocab.name} vocabulary has the same label")
            return Resolution(Constraint(facet, members[0], value, "label_group", tuple(members)))
        if pick in vocab.terms:
            return Resolution(Constraint(facet, pick, value, resolved_by))
        return Resolution(message=f"{pick!r} is not a term of the {vocab.name} vocabulary")
    key = _key(value)
    exact = [t.id for t in vocab.terms.values() if key in {_key(t.id), _key(t.label), *map(_key, t.aliases)}]
    if len(exact) == 1:
        return Resolution(Constraint(facet, exact[0], value, "exact"))
    if exact:
        cands = [_candidate(corpus, vocabs, facet, vocab, tid) for tid in sorted(exact)[:limit]]
        if len({_key(vocab.terms[t].label) for t in exact}) == 1:  # same label in several branches: offer them as one group
            members = tuple(sorted(exact))
            union = Constraint(facet, members[0], value, "label_group", members)
            cands.insert(0, Candidate(GROUP_PREFIX + members[0], vocab.terms[members[0]].label, 0, 0,
                                      len(papers_matching(corpus, [union], vocabs)), f"all {len(members)} terms labelled this"))
        return Resolution(candidates=cands, message=f"{value!r} names {len(exact)} terms; pick one")
    cands = shortlist(corpus, vocabs, facet, value, limit)
    if not cands:
        return Resolution(message=f"no candidate term for {value!r} in the {vocab.name} vocabulary")
    return Resolution(candidates=cands, message=f"{value!r} is not a term of the {vocab.name} vocabulary; pick a candidate")
