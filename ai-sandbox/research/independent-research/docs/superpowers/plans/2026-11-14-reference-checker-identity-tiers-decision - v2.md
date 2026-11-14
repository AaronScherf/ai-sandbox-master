# Reference checker: identity tiers and reference-list linking (decision record, v2)

Date: 2026-11-14. Decided by Aaron (owner). Design only; nothing implemented. Supersedes `2026-11-14-reference-checker-identity-tiers-decision.md` (kept unchanged). Follows `2026-11-11-reference-checker-claude-review-handoff - v5.md`, section 4 (remaining risks).

## Decisions

1. **`SAME_WORK` splits into three tiers.** Nothing passes automatically except CONFIRMED.
   - **CONFIRMED:** title score >= 0.92, or >= 0.5 with the cited year agreeing with the registry.
   - **PLAUSIBLE:** first author and year agree, but no title is available for the citation. Always reviewed by a human or a quote-anchored check; never an automatic pass.
   - **REVIEW:** title score < 0.5, or the year differs. Routed to the interactive review artifact.
2. **0.5 is accepted as a starting cut.** Evidence: four real matches with title scores under 0.5 (Brown, Lopez, Montiel Olea, Rosenzweig and Udry; preprint versus published titles) and one crafted probe (score 0.29, wrong paper). Revisit with a larger sample.
3. **A linking pass runs before PLAUSIBLE is assigned** (new in v2, Aaron 2026-11-14): if the note has a title elsewhere, use it, so only rows with no available title reach PLAUSIBLE.
4. Earlier decisions stand: identity and `text_fidelity` stay separate; author-year-only citations are never `MATCH`; `AMBIGUOUS` rows go to the review artifact.

## Why PLAUSIBLE is expected to be large

Author-year inline citations are the common format, and AI agents copy it. All seven DOI rows in the Literature Gap Memo have no title. A wrong DOI by the right first author passes an author-only check, so author-only agreement cannot be a pass.

## The linking pass

For each inline author-year citation with no title, look for matching entries in the same note's reference list. The key is the normalized first-author surname plus the year (use co-author names when the inline citation gives them, and `a`/`b` suffixes when present).

| Situation | Handling |
|---|---|
| Exactly one list entry matches | Link it. Compare that entry's title with the registry title; apply the CONFIRMED / REVIEW rules above. |
| A list entry contains the same DOI as the inline citation | Strongest link; link by DOI. |
| Two or more list entries match (same author, same year) | Compare the DOI's registry title with each entry. If exactly one scores >= 0.92, that entry resolves the ambiguity. If none or several do, send to REVIEW. |
| No list entry matches, or the note has no reference list with titles | Stays PLAUSIBLE. |

Safety property: the registry title is always compared with the linked entry's title. A wrong link produces a title mismatch and a REVIEW, never a false pass.

Each row records how it was confirmed in a new field, `evidence`: `title_in_citation`, `list_entry`, or `doi_in_list`. Reviewers see what the pass rested on.

Limits (stated, not fixed): the pass checks that the note is internally consistent. A correct list entry paired with the wrong claim is not caught; that needs the quote-anchored claim check. The Literature Gap Memo has no list titles, so its rows stay PLAUSIBLE. The Gemini v2 notes have real reference lists and should benefit most.

## Still open

- **Review volume:** the review artifact must show registry title, authors, year and venue next to the cited text and the claim.
- **Compatibility:** the legacy `classification` field (MATCH, PARTIAL, MISMATCH) and the JSON schema need a migration plan before the tiers and `evidence` field are added. Consumers have not been identified (the checker is unwired).
- **Gate placement** is still inferred from filenames; the evidence-map design docs had not been read when this was written.

## Out of scope

Implementation, building the review artifact, any LLM call, pipeline or CI wiring.
