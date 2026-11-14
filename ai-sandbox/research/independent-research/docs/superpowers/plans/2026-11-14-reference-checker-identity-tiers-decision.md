# Reference checker: identity tiers (decision record)

Date: 2026-11-14. Decided by Aaron (owner). Design only; nothing implemented. Follows `2026-11-11-reference-checker-claude-review-handoff - v5.md`, section 4 (remaining risks).

## Decision

1. `SAME_WORK` splits into three tiers. Nothing passes automatically except the first.
   - **CONFIRMED:** title score >= 0.92, or title score >= 0.5 with the cited year agreeing with the registry.
   - **PLAUSIBLE:** first author (and year) agree, but the citation has no title (`NO_TITLE`). **Always reviewed by a human or by a quote-anchored check; never an automatic pass.**
   - **REVIEW:** title score < 0.5, or the year differs. Routed to the interactive review artifact.
2. The 0.5 cut is accepted as a starting value. It rests on four real data points (Brown, Lopez, Montiel Olea, Rosenzweig and Udry: correct citations with title scores under 0.5) and one crafted probe (score 0.29, wrong paper). Revisit with a larger sample.
3. Existing decisions stand: identity and `text_fidelity` stay separate; author-year-only citations are never `MATCH`; `AMBIGUOUS` rows go to the review artifact.

## Why PLAUSIBLE is expected to be large

Author-year inline citations are the common format, and AI agents copy it. In the Literature Gap Memo every one of the seven DOI rows is `NO_TITLE`. A wrong DOI by the right first author passes an author-only check, so author-only agreement cannot be a pass. The tiers make that explicit instead of hiding it inside `SAME_WORK`.

## Consequences to design for (not yet decided)

- **Review volume.** PLAUSIBLE will dominate. The review artifact must show, per row, the registry title, authors, year and venue next to the cited text and the claim, so a reviewer can decide quickly.
- **Cheaper evidence upstream.** Where an inline citation (Smith 2020) has a matching full reference-list entry in the same note, the checker should use that entry's title before falling back to author-year only. Many PLAUSIBLE rows could become CONFIRMED this way. Open question: how to link inline cites to list entries without guessing.
- **Compatibility.** The legacy `classification` field (MATCH, PARTIAL, MISMATCH) and the JSON schema need a migration plan before the tiers are added; consumers have not been identified (the checker is unwired).
- **Gate placement** is still inferred from filenames; the evidence-map design docs have not been read.

## Out of scope

Implementation, the review artifact build, any LLM call, pipeline or CI wiring.
