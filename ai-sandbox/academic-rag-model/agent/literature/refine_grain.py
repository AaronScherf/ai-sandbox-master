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


def _subtree_listing(vocab, root_ids: set[str]) -> str:
    """Every term in `vocab` whose top-level ancestor is in `root_ids` (the roots themselves included), full
    depth, no LISTING_LIMIT collapse -- one `- id: label` line per term."""
    lines = [f"- {t.id}: {t.label}" + (f" - {t.definition}" if t.definition else "")
             for t in vocab.terms.values() if _root(t.id, vocab) in root_ids]
    return "\n".join(lines)


def _vocab_listing_for(record: dict, vocabs: dict) -> str:
    """The scoped intervention/outcome listing for one paper's refine card. Falls back to stage._vocab_listing's
    existing grouping-only rendering for a facet when scope_roots finds nothing to anchor on (should not occur in
    practice -- every paper carries a sector fact -- but keeps today's behavior as a safety net rather than
    showing an empty listing)."""
    from .stage import _vocab_listing

    sector_vocab = vocabs.get("sector")
    lines: list[str] = []
    for facet in ("intervention", "outcome"):
        vocab = vocabs.get(facet)
        if vocab is None:
            continue
        roots = scope_roots(record, facet, vocab, sector_vocab)
        if roots:
            lines += ["", f"Vocabulary {facet} (version {vocab.version}, {vocab.provenance}; scoped to this "
                           "paper's own category, full depth, no grouping collapse):",
                      _subtree_listing(vocab, roots)]
        else:
            # facet name and vocabulary name coincide for intervention/outcome (schema.FACETS maps each to
            # itself), so this single-entry dict is exactly what stage._vocab_listing expects.
            lines.append(_vocab_listing({facet: vocab}))
    return "\n".join(lines)
