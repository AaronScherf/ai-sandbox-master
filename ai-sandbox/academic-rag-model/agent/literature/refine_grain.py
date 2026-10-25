"""Stage: re-extract only intervention/outcome, scoped to a full (untruncated) vocabulary branch per paper, so the
extractor can pick a specific term instead of defaulting to the coarse bucket stage.py's grouping-only listing
forces it into for a vocabulary over LISTING_LIMIT (docs/superpowers/specs/literature_taxonomy/
2026-10-25-grain-refinement-design.md, TODO-0085)."""
from __future__ import annotations


def _root(term_id: str | None, vocab) -> str | None:
    """`term_id`'s top-level ancestor (a term with no parent) in `vocab`, or None when `vocab` is None, `term_id`
    is None, or `term_id` isn't one of `vocab`'s terms."""
    if vocab is None or term_id is None or term_id not in vocab.terms:
        return None
    seen: set[str] = set()
    cur = term_id
    while vocab.terms[cur].parent and vocab.terms[cur].parent not in seen:
        seen.add(cur)
        cur = vocab.terms[cur].parent
    return cur


def _root_ids_from_facts(facts: list[dict] | None, vocab) -> set[str]:
    """The root of every fact's `vocab_id` in `facts`. A `proposed: true` fact has no `vocab_id` and contributes
    nothing -- it cannot anchor a branch."""
    return {r for f in (facts or []) if (r := _root(f.get("vocab_id"), vocab))}


def _root_by_label(vocab, label: str) -> str | None:
    """The id of `vocab`'s root term (parent is None) whose label equals `label`, or None. Matching by label, not
    id, because the 3ie taxonomy's ids for the same real-world category are not consistent across vocabularies
    (e.g. intervention's "Public Administration" root is `intervention.public_administration_2`, but outcome's
    and sector's are not `_2`-suffixed)."""
    if vocab is None:
        return None
    for term in vocab.terms.values():
        if term.parent is None and term.label == label:
            return term.id
    return None


def scope_roots(record: dict, facet: str, vocab, sector_vocab) -> set[str]:
    """Root ids in `vocab` to show in full for this paper's `facet` listing: the roots of its own current facts in
    that facet; if it has none, the roots (matched by label) implied by its `sector` facts instead. Empty when
    neither exists -- the caller then falls back to today's grouping-only listing for this facet."""
    core = record.get("core") or {}
    own = _root_ids_from_facts(core.get(facet), vocab)
    if own:
        return own
    sector_facts = core.get("sector") or []
    sector_ids = {f.get("vocab_id") for f in sector_facts if f.get("vocab_id")}
    labels = {sector_vocab.terms[sid].label for sid in sector_ids
              if sector_vocab is not None and sid in sector_vocab.terms}
    return {r for label in labels if (r := _root_by_label(vocab, label))}
