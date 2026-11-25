# Reference checker: project history

How the checker came to be, in the order the decisions were made. Each step links its record, so the reasoning can be checked against the source. Usage is covered in [README.md](README.md).

The project has run since 2026-11-11, across three agents:
- **Codex** built and tested the code.
- **Claude** reviewed it, made the design calls with Aaron, built the review page and integrated the work.
- **Gemini** wrote the research notes being checked.

## Website landing gate (2026-11-25)

The [website gate design v2](2026-11-25-website-citation-gate-design%20-%20v2.md) chose a local landing tool instead of a CI job. The owner's citation decisions live in a local, untracked ledger. CI cannot read those decisions and would reopen accepted items; publishing the ledger would expose review state in a public repository. The local tool checks before merging or pushing, using the shared ledger and an owner-approved change ID.

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

## 8. The first full sweep (2026-11-19 to 11-22)

v14 fixed two ledger faults that Claude's probes found:
- A failed lookup now keeps an item's prior state, including a human defect.
- An accepted item reopens only when its evidence changes: the tier, the citation text, or the registered title, authors, year or venue. A shifted line number no longer reopens it.

The same commit corrected the three invented titles in RQ1 and RQ3. Every agent's instruction file then got a "Citing literature" section: the root `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`, and the website's `GEMINI.md`. v15 specified a `--check-references` option for journal discovery; it has not been implemented.

v16 swept the latest version of every research note with a DOI. The sweep found eight real citation errors, which were corrected on `claude/citation-error-fixes`:
- a wrong Pritchett & Sandefur DOI in the Narrative and slides;
- wrong Crost et al. and Bold et al. rows, corrected in Context Distance Cases v2;
- a wrong Bailey et al. row, corrected in Adversarial Scan v2.

It also produced a batch of false positives, which v16 fixed:
- a venue read as a title;
- a short title prefix not counted as a match;
- comparison prose read as a title;
- Markdown left on the end of a DOI;
- adjacent links run together.

v16 added the **Quoted on purpose** decision, for review notes that quote a wrong citation in order to correct it. Claude's review found a regression in which invented titles passed after author-year formatting; it was fixed before landing.

- Handoffs v14–v16; acceptance: `S/2026-11-22-reference-checker-v16-acceptance.md`
- Landed on `main` at `ca9e6eea`.

## 9. Only queue what a person can decide (2026-11-22 to 11-23)

The v16 sweep left 60 open items. Most were a surname and a year. Aaron's 8 decisions on rows like that had all been accepts, and both real catches had come from rows with titles. So v17 let title-less rows pass on author and year, whatever siblings the same team had. It also used venue, volume and pages as agreement or conflict, passed descriptive links that share words with the registered title (DESCRIBED), and reported the review load after each `raise`. Claude's review caught three bugs and one regression before landing:
- venue-less rows matched to siblings;
- "AEA P&P" read as a title;
- an accept rate that could never be computed;
- a title containing its journal's name read as the venue.

The live sweep cut the page from 60 items to 20.

- Handoff v17; review and acceptance: `S/2026-11-23-reference-checker-v17-review.md`
- Landed on `main` at `6ced8bb4`.

## 10. A DOI does not show what was meant (2026-11-23)

Reviewing the remaining 20, Aaron found that name, year and DOI could not tell him what Gemini meant to cite. Some DOIs were plainly unrelated. Some citations matched a real paper by the same authors and year that the DOI did not point to. Gemini seemed to invent a DOI when it couldn't find one. So passing a row because the DOI is by those authors in that year, as v17 does, rests on evidence that the writer cannot be trusted to supply.

The decision was to move the burden to the writer. In a note a branch adds or edits, a citation must carry the title of the work the writer means, looked up from that work rather than read off the DOI's record. A missing title is a defect the writer fixes, not an item a reviewer guesses at. Whether the paper supports the claim is a separate design, recorded as a pending to-do (a download-and-transcribe queue ordered by how much a claim matters and how unsure the reviewer is).

- Handoff v18; evidence: `S/2026-11-23-reference-checker-v17-review.md` section 6.

## State at 2026-11-23

- The review page has 12 deferred items in existing notes. They block nothing unless someone edits those notes.
- `claude/citation-error-fixes` passes its landing check and waits for approval.
- v18 is handed to Codex.

**Still open:**
- the claim check (pending to-do, `## Claim Support Check`);
- resolving plain URLs;
- v15 (discovery `--check-references`);
- a routing line in `docs/AGENT_ROUTING.md`, deferred until `claude/spec-a-research-profile` lands, to avoid an overlap.
