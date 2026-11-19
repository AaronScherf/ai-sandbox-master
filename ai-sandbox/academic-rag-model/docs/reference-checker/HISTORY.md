# Reference checker: project history

How the checker came to be, in the order the decisions were made. Each step links its record, so the reasoning can be checked against the source. Usage is covered in [README.md](README.md).

The project ran from 2026-11-11 to 2026-11-18, across three agents:
- **Codex** built and tested the code.
- **Claude** reviewed it, made the design calls with Aaron, built the review page and integrated the work.
- **Gemini** wrote the research notes being checked.

Paths below are relative to the repository root. The handoff series is the main thread: each version is a new file, and none was edited after it was committed.

```text
P = ai-sandbox/research/independent-research/docs/superpowers/plans/
S = ai-sandbox/academic-rag-model/docs/status/tools/
```

## 1. The problem (2026-11-11)

Gemini wrote four novelty-check notes for a PhD research agenda and tagged every reference `[VERIFIED]`. Claude resolved the 38 `doi.org` links against Crossref. Only 13 resolved to the cited paper; 13 resolved to a different paper and 12 did not resolve. Gemini's correction pass fixed about 30 references but introduced new errors, and its report still claimed every DOI matched. Conclusion: an agent's own claim of verification is worth nothing. Verification has to be mechanical.

- Codex work order: `P/2026-11-11-reference-checker-codex-handoff.md`
- Second regression set (errors that survived a correction round): `P/2026-11-11-reference-checker-regression-addendum.md`

## 2. Building a conservative checker (handoffs v1–v5, 2026-11-11 to 11-14)

Claude reviewed Codex's checker in rounds. The main points:
- Query the registry that actually issued each DOI (Crossref, DataCite, arXiv) instead of assuming Crossref.
- Send only identifiers, never note text.
- Cache responses.
- Treat a lookup failure as "unresolved", never as a pass.

v2 withdrew a v1 claim: the "mojibake" Claude had reported came from its own console encoding, not from the notes. v4 corrected Claude's overbroad expectation that none of the Memo's rows could be WRONG_WORK. v5 judged the checker ready to land as an advisory tool, not yet as a gate.

- `P/2026-11-11-reference-checker-claude-review-handoff - v1.md` through `- v5.md`

## 3. Tiers and the review page (2026-11-14 to 11-15)

Aaron decided that a SAME_WORK match is not one thing. CONFIRMED needs a strong title match. A citation with no title (PLAUSIBLE) or with a low title score (REVIEW) goes to a person. Separately, a linking pass borrows titles from the note's own reference list.

The review unit is one row per DOI per note. "Same work" carries over to identical citations in other notes, and "wrong work" stays with its note. Decisions are made on an interactive page, never by editing JSON.

- `P/2026-11-14-reference-checker-identity-tiers-decision.md`, `- v2.md`
- `P/2026-11-14-reference-checker-review-artifact-plan.md`, `- v2.md`
- Implementation and review: handoffs v6 (work order), v7 (land after a year-tolerance fix) and v8 (results on real notes)

## 4. The ledger (2026-11-15)

Codex built `tools/reference_review.py`, which raises items, applies decisions and records defects. Claude built the review page as a Claude Artifact, with decisions stored in the page's database.

- Handoff v9; acceptance: `S/2026-11-15-reference-review-acceptance.md`

## 5. Title-less citations pass on author and year (2026-11-16)

After the first review, Aaron observed that checking a title-less row by hand means opening the DOI and comparing the title, which is exactly what the checker already does. So a title-less row now passes as AUTHOR_YEAR if every surname is registered, the year matches exactly, and the DOI is in Crossref.

A *same-team guard* came with it. If the same team published a different paper within a year either side, the citation could mean either one, so the row stays in review and the page lists the alternatives.

- `P/2026-11-14-reference-checker-identity-tiers-decision - v3.md`; handoff v10
- Acceptance: `S/2026-11-17-reference-checker-author-year-acceptance.md`

## 6. Making the guard complete (2026-11-18)

Codex blocked its own landing. A relevance-ranked Crossref author search cannot prove that no sibling exists, and two rows (Groh 2016, Raleigh 2015) passed when they should not have. The ruling was to take completeness from OpenAlex author IDs: list every work by the first author in the window, and fail closed on any gap.

The rule for when a sibling counts as "a different paper" then had to be tightened. A version-title threshold of 0.5 let shared boilerplate (for example, "Evidence from ...") pass different papers off as versions of one, so it was raised to 0.8.

- Handoff v11; acceptance: `S/2026-11-18-reference-checker-openalex-acceptance.md`

## 7. Invented titles and the landing gate (2026-11-18)

Aaron's review declined two citations as "wrong paper". Their authors, year, journal and DOI were all right; only the title was wrong. A search of Crossref and OpenAlex found neither title anywhere: Gemini had invented a plausible title for a real paper. That needed its own decision ("Title wrong, DOI right"), and the checker now searches for any low-scoring cited title. If the title exists nowhere, the row becomes a TITLE_WRONG defect. The search found a third case of the same kind (Brown et al. 2025).

Until then, nothing called the checker unless an agent chose to run it, the same weakness the project had started from. v13 added a gate to `tools.land_branch`. A branch that changes a note under `ai-sandbox/research/` cannot land while that note has a defect, an open review item or a failed lookup. `GEMINI.md` gained a "Citing literature" section telling Gemini to run the checker before handoff.

- Handoffs v12 and v13; acceptance: `S/2026-11-18-reference-checker-title-gate-acceptance.md`
- Landed on `main` at `ca422ff0`.

## State at 2026-11-18

Five notes have been checked: RQ1 v4, RQ2 v4, RQ3 v5, the Summary v3 and the Literature Gap Memo v2. There are no open review items. Ten citations were accepted by hand. Three TITLE_WRONG defects are waiting on a fix to the notes: Lopez et al. and Brown et al. in RQ1, and Rosenzweig & Udry in RQ3. Until they are fixed, any new version of those two notes will be stopped at landing.

**Still open:**
- a claim check, i.e. whether each paper supports what it is cited for;
- resolving plain URLs;
- a routing line in `docs/AGENT_ROUTING.md`, deferred until `claude/spec-a-research-profile` lands, to avoid an overlap;
- keeping a decided item closed when a later title search fails transiently.
