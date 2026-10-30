"""Direct, adjacent, different-method and partial papers for a set of resolved constraints, and the corpus-only verdict."""
from __future__ import annotations

from dataclasses import dataclass, field

from .adjacent import widen
from .corpus import Corpus
from .match import Constraint, fact_matches
from .subregions import Subregions

RELAXABLE = ("intervention", "outcome", "countries")
PARTIAL_CAP = 10


@dataclass
class GapResult:
    direct: list[str] = field(default_factory=list)
    adjacent: dict[str, list[str]] = field(default_factory=dict)  # file id -> one label per qualifying relaxation
    different_method: list[str] = field(default_factory=list)
    partial: list[tuple[str, int]] = field(default_factory=list)  # (file id, constraints matched exactly)
    unwidenable: list[str] = field(default_factory=list)  # "facet=value" of relaxable constraints that cannot be widened
    verdict: str = "no_evidence_in_corpus"
    rule: str = ""


def classify(corpus: Corpus, constraints: list[Constraint], vocabs: dict, subregions: Subregions) -> GapResult:
    exact = {fid: [any(fact_matches(c, f, vocabs) for f in facts) for c in constraints]
             for fid, facts in corpus.facts.items()}
    result = GapResult(direct=sorted(fid for fid, hit in exact.items() if all(hit)))
    widenings = {i: widen(c, vocabs, subregions) for i, c in enumerate(constraints) if c.facet in RELAXABLE}
    result.unwidenable = [f"{constraints[i].facet}={constraints[i].value}" for i, w in widenings.items() if w is None]
    design = [i for i, c in enumerate(constraints) if c.facet == "study_design"]
    for fid in sorted(exact):
        if fid in result.direct:
            continue
        hit, facts = exact[fid], corpus.facts[fid]
        labels = []
        for i, w in widenings.items():
            if w is None or not all(h for j, h in enumerate(hit) if j != i):
                continue
            matched = next((f for f in facts if w.matches(f, vocabs)), None)
            if matched is not None:
                labels.append(w.label_for(matched, vocabs))
        if labels:
            result.adjacent[fid] = labels
        elif design and len(design) < len(constraints) and all(h for j, h in enumerate(hit) if j not in design):
            result.different_method.append(fid)
    placed = set(result.direct) | set(result.adjacent) | set(result.different_method)
    year = lambda fid: corpus.papers[fid].year or 0 if fid in corpus.papers else 0
    partial = [(fid, sum(hit)) for fid, hit in exact.items() if fid not in placed and sum(hit) >= 1]
    result.partial = sorted(partial, key=lambda p: (-p[1], -year(p[0]), p[0]))[:PARTIAL_CAP]
    if result.direct:
        result.verdict = "tried_directly"
        result.rule = f"{len(result.direct)} paper{'s' if len(result.direct) != 1 else ''} match every constraint (descendants included)."
    elif result.adjacent:
        result.verdict = "tried_adjacent"
        result.rule = (f"No paper matches every constraint; {len(result.adjacent)} match with exactly one relaxable "
                       "constraint widened to its siblings or subregion.")
    else:
        result.rule = ("No paper matches every constraint, or all but one with that constraint widened. "
                       "This covers the corpus only.")
    return result
